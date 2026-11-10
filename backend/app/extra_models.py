"""Operational outbox, integrations, legal content and private document metadata.

Financial and fiscal acknowledgment is *never* inferred from an outbound request.
"""
from .extensions import db
from .models import new_id, utcnow
from sqlalchemy import CheckConstraint

class ProviderAttempt(db.Model):
    __tablename__ = "provider_attempts"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    payment_id = db.Column(db.String(36), db.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, unique=True)
    provider = db.Column(db.String(20), nullable=False)
    reference = db.Column(db.String(100), nullable=False, unique=True)
    requested_amount_ugx = db.Column(db.BigInteger, nullable=False)
    msisdn = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="INITIATED")
    verification_attempts = db.Column(db.Integer, nullable=False, default=0)
    last_verified_at = db.Column(db.DateTime(timezone=True))
    last_error_code = db.Column(db.String(80))
    last_response_digest = db.Column(db.String(64))
    provider_transaction_id = db.Column(db.String(150), unique=True, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("requested_amount_ugx > 0", name="ck_provider_amount"),)

class FiscalSubmission(db.Model):
    __tablename__ = "efris_submissions"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    invoice_id = db.Column(db.String(36), db.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    document_type = db.Column(db.String(30), nullable=False, default="INVOICE")
    idempotency_key = db.Column(db.String(128), nullable=False, unique=True)
    state = db.Column(db.String(30), nullable=False, default="PENDING_FISCALIZATION")
    payload = db.Column(db.JSON, nullable=False, default=dict)
    accepted_metadata = db.Column(db.JSON, nullable=False, default=dict)
    fiscal_document_number = db.Column(db.String(120))
    verification_url = db.Column(db.String(800))
    qr_payload = db.Column(db.Text)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime(timezone=True))
    last_error_code = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    acknowledged_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (db.UniqueConstraint("invoice_id", "document_type", name="uq_fiscal_document_intent"),)

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    channel = db.Column(db.String(15), nullable=False)
    kind = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(25), nullable=False, default="PENDING")
    dedupe_key = db.Column(db.String(160), nullable=False, unique=True)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime(timezone=True))
    last_error_code = db.Column(db.String(80))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    delivered_at = db.Column(db.DateTime(timezone=True))
    read_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (CheckConstraint("attempt_count >= 0", name="ck_notification_attempts"),)

class WorkOrder(db.Model):
    __tablename__ = "work_orders"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    request_id = db.Column(db.String(36), db.ForeignKey("maintenance_requests.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    contractor_name = db.Column(db.String(200))
    scope = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="OPEN")
    estimated_cost_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    actual_cost_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (CheckConstraint("estimated_cost_ugx >= 0 AND actual_cost_ugx >= 0", name="ck_work_cost"),)

class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    owner_user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    tenant_id = db.Column(db.String(36), db.ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)
    lease_id = db.Column(db.String(36), db.ForeignKey("leases.id", ondelete="RESTRICT"))
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"))
    category = db.Column(db.String(30), nullable=False)
    object_key = db.Column(db.String(200), nullable=False, unique=True)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(25), nullable=False, default="AWAITING_UPLOAD")
    object_version_id = db.Column(db.String(300))
    scan_completed_at = db.Column(db.DateTime(timezone=True))
    size_bytes = db.Column(db.BigInteger)
    checksum_sha256 = db.Column(db.String(64))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("size_bytes IS NULL OR size_bytes BETWEEN 0 AND 8388608", name="ck_document_size"),)

class LegalPage(db.Model):
    __tablename__ = "legal_pages"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    slug = db.Column(db.String(60), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    published = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint("slug", "version", name="uq_legal_version"),)

class SystemSetting(db.Model):
    __tablename__ = "system_settings"
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON, nullable=False)
    updated_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ContactRequest(db.Model):
    __tablename__ = "contact_requests"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(30))
    subject = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    consent = db.Column(db.Boolean, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="NEW")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at = db.Column(db.DateTime(timezone=True))


from sqlalchemy import Index
Index("ix_documents_tenant_created", Document.tenant_id, Document.created_at)
Index("ix_notifications_user_created", Notification.user_id, Notification.created_at)
