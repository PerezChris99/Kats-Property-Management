"""Reconcile verified mobile money status against invoice and immutable ledger.

An accepted payment request (or any unauthenticated webhook) never credits a
tenant. Only an independently fetched final provider status can post funds.
"""
from datetime import datetime, timezone
import hashlib
import json
from sqlalchemy.exc import IntegrityError
from .extensions import db
from .models import Invoice, Payment, LedgerEntry, AuditLog
from .extra_models import ProviderAttempt
from .providers import provider, ProviderError

class SettlementError(RuntimeError):
    pass

def verify_and_post(payment_id):
    attempt = db.session.query(ProviderAttempt).join(Payment, Payment.id == ProviderAttempt.payment_id).filter(
        ProviderAttempt.payment_id == payment_id
    ).first()
    if attempt is None:
        raise SettlementError("Mobile payment attempt not found")
    payment = db.session.get(Payment, attempt.payment_id)
    if payment.status == "RECONCILED":
        return {"state":"RECONCILED","credited":True}
    if payment.status in ("REVERSED","CANCELLED"):
        return {"state":payment.status,"credited":False}
    try:
        result = provider(attempt.provider).status(attempt.reference, attempt.requested_amount_ugx)
    except ProviderError as exc:
        # Unknown provider outcome: preserve payment for later reconciliation.
        attempt.verification_attempts += 1
        attempt.status = "RETRYING"
        attempt.last_error_code = "PROVIDER_UNAVAILABLE"
        attempt.last_verified_at = datetime.now(timezone.utc)
        db.session.commit()
        return {"state":"RETRYING","credited":False}
    # Serialize financial mutation: lock provider attempt, then payment, then invoice.
    attempt = db.session.query(ProviderAttempt).filter_by(payment_id=payment_id).with_for_update().first()
    payment = db.session.query(Payment).filter_by(id=attempt.payment_id).with_for_update().first()
    if payment.status == "RECONCILED":
        return {"state":"RECONCILED","credited":True}
    attempt.verification_attempts += 1
    attempt.last_verified_at = datetime.now(timezone.utc)
    attempt.last_error_code = result.reason[:80] if result.reason else None
    attempt.status = result.state
    if result.state == "FAILED":
        payment.status = "FAILED"
    elif result.state == "SUCCESSFUL":
        invoice = db.session.query(Invoice).filter_by(id=payment.invoice_id).with_for_update().first()
        # Another payment may have settled while this one was pending.
        if (invoice is None or invoice.status == "VOID" or
                payment.amount_ugx > invoice.total_ugx-invoice.credit_ugx-invoice.paid_ugx):
            payment.status = "UNRECONCILED"
            attempt.status = "UNRECONCILED"
            attempt.last_error_code = "INVOICE_BALANCE_CONFLICT"
        elif payment.status not in ("REVERSED","FAILED"):
            invoice.paid_ugx += payment.amount_ugx
            invoice.status = "PAID" if invoice.paid_ugx + invoice.credit_ugx == invoice.total_ugx else "PARTIALLY_PAID"
            payment.status = "RECONCILED"
            attempt.provider_transaction_id = result.transaction_id
            db.session.add(LedgerEntry(invoice_id=invoice.id, payment_id=payment.id,
                                       event="PAYMENT_RECEIVED", amount_ugx=payment.amount_ugx))
            db.session.add(AuditLog(actor_id=payment.created_by, action="provider.payment_verified",
                                    target_type="payment", target_id=payment.id,
                                    details={"provider":attempt.provider,
                                             "reference":attempt.reference,
                                             "verified_financial_transaction_id":result.transaction_id}))
    elif result.state == "UNVERIFIED":
        # A provider response missing trusted details must NOT credit the tenant.
        payment.status = "UNRECONCILED"
    else:
        payment.status = "PENDING_PROVIDER"
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise SettlementError("Provider settlement requires manual reconciliation")
    return {"state":payment.status,"credited":payment.status == "RECONCILED"}
