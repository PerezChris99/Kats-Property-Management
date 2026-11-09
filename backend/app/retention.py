"""Bounded cleanup for expired temporary credentials.

Do NOT delete invoices, accounting events, audit history, settlements, fiscal
records, deposits or business/legal documents. This task only removes ephemeral
session and one-use account-token rows after a 30-day investigation window.
"""
from datetime import timedelta
from sqlalchemy import or_
from .extensions import db
from .models import RefreshSession, utcnow
from .account_models import AccountToken

DEFAULT_RETENTION_DAYS=30
BATCH_LIMIT=300
MAX_BATCHES=2

def prune_ephemeral_credentials(retention_days=DEFAULT_RETENTION_DAYS,
                                batch_size=BATCH_LIMIT):
    if type(retention_days) is not int or not 7 <= retention_days <= 365:
        raise ValueError("Retention must be between 7 and 365 days")
    if type(batch_size) is not int or not 1 <= batch_size <= BATCH_LIMIT:
        raise ValueError("Batch limit must be between 1 and 300")
    cutoff=utcnow()-timedelta(days=retention_days)
    counts={"refresh_sessions":0,"account_tokens":0}
    configs=(
        (RefreshSession,or_(RefreshSession.expires_at<cutoff,
                            RefreshSession.revoked_at<cutoff),"refresh_sessions"),
        (AccountToken,or_(AccountToken.expires_at<cutoff,
                          AccountToken.consumed_at<cutoff),"account_tokens"),
    )
    for model,condition,label in configs:
        for _ in range(MAX_BATCHES):
            ids=[x[0] for x in db.session.query(model.id).filter(condition).order_by(
                model.expires_at,model.id).limit(batch_size).all()]
            if not ids:
                break
            count=db.session.query(model).filter(model.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
            counts[label]+=count
            if len(ids)<batch_size:
                break
    return counts
