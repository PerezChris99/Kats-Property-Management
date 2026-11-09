"""Replaceable URA EFRIS gateway and retryable fiscal outbox.

An approved URA system-to-system adapter MUST be installed and registered.
A queued request is not an EFRIS fiscal receipt; only authenticated URA
acknowledgment can mark the record ACCEPTED.
"""
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from flask import current_app
from sqlalchemy import or_
from .extensions import db
from .models import Invoice, InvoiceLine, AuditLog
from .extra_models import FiscalSubmission
from .billing import system_actor

@dataclass(frozen=True)
class FiscalReply:
    """Verified fields returned by an approved taxpayer-specific URA connector."""
    status: str
    fiscal_document_number: str|None = None
    qr_payload: str|None = None
    verification_url: str|None = None
    error_code: str|None = None
    provider_response_id: str|None = None
    authenticated: bool = False

class FiscalAdapterUnavailable(RuntimeError):
    pass

_adapter_factory=None

def register_efris_adapter(factory):
    """Call only from the approved URA adapter package integration startup."""
    global _adapter_factory
    _adapter_factory=factory

def gateway():
    if os.getenv("EFRIS_ENABLED","false").lower()!="true":
        raise FiscalAdapterUnavailable("EFRIS disabled until taxpayer registration and URA acceptance")
    if _adapter_factory is None:
        raise FiscalAdapterUnavailable("Approved URA adapter is not installed")
    return _adapter_factory()

def run_fiscal_batch(adapter=None, maximum=20, now=None):
    now=now or datetime.now(timezone.utc)
    if adapter is None:
        try:
            adapter=gateway()
        except FiscalAdapterUnavailable:
            return {"processed":0,"accepted":0,"waiting_for_ura_adapter":True}
    if type(maximum) is not int or not 1<=maximum<=100:
        raise ValueError("Invalid fiscal batch limit")
    records=db.session.query(FiscalSubmission).filter(
        FiscalSubmission.state.in_(["PENDING_FISCALIZATION","RETRYING"]),
        or_(FiscalSubmission.next_attempt_at.is_(None),
            FiscalSubmission.next_attempt_at<=now)
    ).order_by(FiscalSubmission.created_at).limit(maximum).all()
    processed=0
    accepted=0
    for item in records:
        invoice=db.session.get(Invoice,item.invoice_id)
        if not invoice or invoice.status=="VOID":
            item.state="REJECTED"
            item.last_error_code="INVOICE_VOID"
            db.session.commit()
            continue
        lines=db.session.query(InvoiceLine).filter_by(invoice_id=invoice.id).all()
        if not lines:
            item.state="FAILED"
            item.last_error_code="INVOICE_LINES_MISSING"
            db.session.commit()
            continue
        try:
            # The adapter must implement actual URA signing/encryption, taxpayer
            # identity, certificate management and authenticated response checks.
            response=adapter.submit_invoice(invoice=invoice,lines=lines,
                                             idempotency_key=item.idempotency_key)
        except Exception:
            response=FiscalReply(status="RETRYING",error_code="PROVIDER_UNAVAILABLE")
        item.attempt_count+=1
        processed+=1
        if not isinstance(response,FiscalReply):
            response=FiscalReply(status="RETRYING",error_code="INVALID_ADAPTER_RESPONSE")
        if response.status=="ACCEPTED" and response.authenticated:
            url=urlparse(response.verification_url or "")
            if (not response.fiscal_document_number or not response.qr_payload
                    or url.scheme!="https" or not url.hostname or
                    not (url.hostname=="ura.go.ug" or url.hostname.endswith(".ura.go.ug"))):
                item.state="RETRYING"
                item.last_error_code="FISCAL_PROOF_INCOMPLETE"
            else:
                item.fiscal_document_number=response.fiscal_document_number
                item.qr_payload=response.qr_payload
                item.verification_url=response.verification_url
                item.accepted_metadata={"provider_response_id":response.provider_response_id,
                                        "accepted_at":now.isoformat()}
                item.acknowledged_at=now
                item.state="ACCEPTED"
                item.next_attempt_at=None
                item.last_error_code=None
                db.session.add(AuditLog(actor_id=system_actor().id,
                    action="efris.accepted",target_type="efris_submission",
                    target_id=item.id,details={
                        "invoice_id":invoice.id,
                        "fiscal_number":item.fiscal_document_number,
                        "provider_response_id":response.provider_response_id}))
                accepted+=1
        elif response.status=="REJECTED" and response.authenticated:
            item.state="REJECTED"
            item.last_error_code=(response.error_code or "REJECTED")[:100]
            item.next_attempt_at=None
        else:
            item.state="RETRYING"
            item.last_error_code=(response.error_code or "UNVERIFIED_REPLY")[:100]
        if item.state=="RETRYING":
            if item.attempt_count>=8:
                item.state="FAILED"
                item.next_attempt_at=None
            else:
                item.next_attempt_at=now+timedelta(minutes=min(240,2**item.attempt_count))
        db.session.commit()
    return {"processed":processed,"accepted":accepted,"waiting_for_ura_adapter":False}
