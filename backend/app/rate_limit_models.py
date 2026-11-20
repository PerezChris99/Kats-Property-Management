"""Shared, hashed request counters used only by the PostgreSQL rate limiter."""
from .extensions import db


class RateLimitCounter(db.Model):
    __tablename__ = "rate_limit_counters"
    key_digest = db.Column(db.String(64), primary_key=True)
    hits = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    __table_args__ = (db.CheckConstraint("hits > 0", name="ck_rate_limit_positive_hits"),)
