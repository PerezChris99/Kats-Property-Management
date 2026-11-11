"""Private S3-compatible document uploads and scoped short-lived downloads.

No document payload travels through the Flask API. Never use public ACLs or
unvalidated user-provided object paths. Never cache private signed URLs.
"""
import os
import re
import secrets
from datetime import datetime, timezone
from flask import Blueprint, abort, jsonify
from flask_jwt_extended import jwt_required
from .api import current_user, data, required_string, fail, serialize, audit, list_page
from .extensions import db
from .models import Tenant, Lease, Room, CaretakerAssignment
from .extra_models import Document

documents_api = Blueprint("documents", __name__)
from .malware_scan import scan_bytes, file_magic_matches, ScanUnavailable
# All API blueprints now receive one common authenticated PostgreSQL RLS scope.
ALLOWED_MIMES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
ALLOWED_CATEGORIES = {"LEASE", "ID", "RECEIPT", "INSPECTION", "PAYMENT_PROOF", "ROOM_PHOTO"}
MAX_BYTES = 8 * 1024 * 1024
STAFF = {"OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN"}

def storage():
    bucket = os.getenv("S3_BUCKET")
    endpoint = os.getenv("S3_ENDPOINT_URL")
    if not bucket or not endpoint or not endpoint.startswith("https://"):
        return None, None
    import boto3
    return boto3.client("s3", endpoint_url=endpoint,
                        region_name=os.getenv("S3_REGION", "auto")), bucket

def can_access(user, doc):
    if user.role in STAFF:
        return True
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        return linked is not None and doc.tenant_id == linked
    if user.role == "CARETAKER" and doc.category in ("ROOM_PHOTO", "INSPECTION"):
        return bool(doc.room_id and db.session.query(CaretakerAssignment.id).filter_by(
            caretaker_user_id=user.id, room_id=doc.room_id).first())
    return False

@documents_api.post("/documents/presign")
@jwt_required()
def presign_upload():
    user = current_user()
    obj = data()
    category = required_string(obj, "category", 40).upper()
    mime = required_string(obj, "mime_type", 100).lower()
    filename = required_string(obj, "filename", 255)
    if category not in ALLOWED_CATEGORIES or mime not in ALLOWED_MIMES:
        return fail("Unsupported document category or file format")
    if "/" in filename or "\\" in filename or any(ord(ch) < 32 for ch in filename):
        return fail("Filename contains invalid characters")
    if not re.fullmatch(r"[\w .()\-]{1,255}", filename, flags=re.UNICODE):
        return fail("Use a simple filename without special characters")
    size = obj.get("size_bytes")
    if type(size) is not int or not 1 <= size <= MAX_BYTES:
        return fail("Document must be between 1 byte and 8 MB")
    lease_id = obj.get("lease_id")
    room_id = obj.get("room_id")
    tenant_id = None
    if lease_id:
        lease = db.session.get(Lease, lease_id)
        if not lease:
            abort(404)
        tenant_id = lease.tenant_id
        if room_id and room_id != lease.room_id:
            return fail("Document room conflicts with lease")
        room_id = lease.room_id
    elif room_id:
        room = db.session.get(Room, room_id)
        if not room:
            abort(404)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None or lease_id is None or tenant_id != linked:
            abort(403)
        if category not in ("PAYMENT_PROOF", "INSPECTION", "LEASE"):
            abort(403)
    elif user.role == "CARETAKER":
        if not room_id or not db.session.query(CaretakerAssignment.id).filter_by(
            caretaker_user_id=user.id, room_id=room_id).first():
            abort(403)
        if category not in ("ROOM_PHOTO", "INSPECTION"):
            abort(403)
    elif user.role not in STAFF:
        abort(403)
    client, bucket = storage()
    if client is None:
        return fail("Private document storage is not configured", 503)
    object_key = "kats-private/" + secrets.token_hex(24)
    doc = Document(owner_user_id=user.id, category=category,
                   tenant_id=tenant_id, lease_id=lease_id, room_id=room_id,
                   filename=filename, mime_type=mime, size_bytes=size, object_key=object_key)
    # Sign only exact object key and MIME. Enforce size via POST policy.
    try:
        signed = client.generate_presigned_post(
            Bucket=bucket, Key=object_key,
            Fields={"Content-Type": mime},
            Conditions=[{"Content-Type":mime},["content-length-range",1,MAX_BYTES]],
            ExpiresIn=120,
        )
    except Exception:
        return fail("Unable to initialize private upload", 503)
    db.session.add(doc)
    db.session.flush()
    audit(user, "document.presign", "document", doc.id, category=category)
    db.session.commit()
    return jsonify(document=serialize(doc, "id", "filename", "mime_type", "status"),
                   upload={"url":signed["url"],"fields":signed["fields"],
                           "expires_in_seconds":120}), 201

@documents_api.post("/documents/<doc_id>/complete")
@jwt_required()
def complete_document(doc_id):
    user = current_user()
    doc = db.session.get(Document, doc_id)
    if not doc or not can_access(user, doc):
        abort(404)
    if doc.status == "UPLOADED":
        return jsonify(document=serialize(doc, "id", "status"))
    if doc.status != "AWAITING_UPLOAD":
        return fail("Document not pending upload", 409)
    client, bucket = storage()
    if client is None:
        return fail("Storage not configured", 503)
    try:
        info = client.head_object(Bucket=bucket, Key=doc.object_key)
    except Exception:
        return fail("Upload has not been confirmed by object storage", 409)
    if info.get("ContentLength") != doc.size_bytes or info.get("ContentType", "").lower() != doc.mime_type:
        return fail("Stored file size or type differs from signed policy", 409)
    version_id = info.get("VersionId")
    if not version_id or not isinstance(version_id, str):
        return fail("Private document storage must use immutable S3 object versioning", 503)
    try:
        stored = client.get_object(Bucket=bucket, Key=doc.object_key, VersionId=version_id)
        if stored.get("ContentLength") != doc.size_bytes or stored.get("ContentType","").lower() != doc.mime_type:
            return fail("Uploaded object version differs from signed upload", 409)
        # Bound memory and guarantee scan verdict refers to the immutable
        # version subsequently used for presigned downloads.
        blob = stored["Body"].read(MAX_BYTES+1)
        if len(blob) != doc.size_bytes:
            return fail("Document size changed during verification", 409)
        magic_valid = file_magic_matches(doc.mime_type, blob)
        verdict = scan_bytes(blob) if magic_valid else "INFECTED"
    except ScanUnavailable:
        return fail("Document scanner unavailable. Upload is not approved; retry verification", 503)
    except Exception:
        return fail("Unable to verify private document contents", 503)
    doc.object_version_id = version_id
    doc.scan_completed_at = datetime.now(timezone.utc)
    doc.status = "UPLOADED" if verdict == "CLEAN" else "QUARANTINED"
    audit(user, "document.scan_verified", "document", doc.id, result=verdict)
    db.session.commit()
    if verdict != "CLEAN":
        return fail("Document rejected by security inspection", 409)
    return jsonify(document=serialize(doc, "id", "status"))

@documents_api.get("/documents")
@jwt_required()
def list_documents():
    user = current_user()
    query = db.session.query(Document)
    if user.role == "TENANT":
        linked = db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if not linked:
            return jsonify(items=[], total=0)
        query = query.filter_by(tenant_id=linked)
    elif user.role == "CARETAKER":
        assigned = db.session.query(CaretakerAssignment.room_id).filter_by(caretaker_user_id=user.id)
        query = query.filter(Document.room_id.in_(assigned),
                             Document.category.in_(["ROOM_PHOTO", "INSPECTION"]))
    elif user.role not in STAFF:
        abort(403)
    results = list_page(Document, query.order_by(Document.created_at.desc()))
    return jsonify(items=[serialize(doc,"id","category","filename","mime_type","status","created_at")
                          for doc in results.items],total=results.total)

@documents_api.get("/documents/<doc_id>/download")
@jwt_required()
def document_download(doc_id):
    user = current_user()
    doc = db.session.get(Document, doc_id)
    if (not doc or not can_access(user, doc) or doc.status != "UPLOADED"
            or not doc.scan_completed_at or not doc.object_version_id):
        abort(404)
    client, bucket = storage()
    if client is None:
        return fail("Storage unavailable", 503)
    try:
        url = client.generate_presigned_url("get_object", Params={
            "Bucket":bucket, "Key":doc.object_key,
            "VersionId":doc.object_version_id,
            "ResponseContentDisposition":"attachment"
        }, ExpiresIn=60)
    except Exception:
        return fail("Unable to authorize download", 503)
    return jsonify(url=url, expires_in_seconds=60)
