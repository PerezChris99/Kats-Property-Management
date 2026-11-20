"""Shared PostgreSQL fixed-window rate limits without Redis.

Registered as limits' katsdb:// storage. Use only with migrated PostgreSQL,
never serverless process-local memory. Counters are SHA-256 keyed (no raw IPs),
atomically updated via UPSERT, and stored outside tenant-controlled RLS tables.
"""
from __future__ import annotations

import hashlib
import time
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from limits.storage import Storage

from .extensions import db


class PostgresRateLimitStorage(Storage):
    STORAGE_SCHEME = ["katsdb"]

    def __init__(self, uri: str, **options) -> None:
        if uri != "katsdb://":
            raise ValueError("Unsupported KATS rate-limit store")
        super().__init__(uri, **options)

    @property
    def base_exceptions(self):
        # Do not fall back to process-local in-memory storage when PG is down.
        return (SQLAlchemyError, RuntimeError)

    @staticmethod
    def _key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _engine():
        engine = db.engine
        if engine.dialect.name != "postgresql":
            raise RuntimeError("KATS rate-limit storage requires migrated PostgreSQL")
        return engine

    def incr(self, key: str, expiry: int, elastic_expiry: bool = False,
             amount: int = 1) -> int:
        if amount <= 0 or not 1 <= expiry <= 31536000:
            raise ValueError("Invalid rate-limit counter increment/expiry")
        with self._engine().begin() as connection:
            return int(connection.execute(text("""
                INSERT INTO rate_limit_counters (key_digest, hits, expires_at)
                VALUES (:key, :amount, now() + CAST(:expiry AS INTEGER) * INTERVAL '1 second')
                ON CONFLICT (key_digest) DO UPDATE SET
                    hits = CASE WHEN rate_limit_counters.expires_at <= now()
                                THEN EXCLUDED.hits
                                ELSE rate_limit_counters.hits + EXCLUDED.hits END,
                    expires_at = CASE WHEN rate_limit_counters.expires_at <= now()
                                         OR :elastic
                                      THEN EXCLUDED.expires_at
                                      ELSE rate_limit_counters.expires_at END
                RETURNING hits
            """), {
                "key": self._key(key),
                "amount": amount,
                "expiry": expiry,
                "elastic": bool(elastic_expiry),
            }).scalar_one())

    def get(self, key: str) -> int:
        with self._engine().connect() as connection:
            return int(connection.execute(text("""
                SELECT CASE WHEN expires_at > now() THEN hits ELSE 0 END
                FROM rate_limit_counters WHERE key_digest = :key
            """), {"key": self._key(key)}).scalar() or 0)

    def get_expiry(self, key: str) -> float:
        with self._engine().connect() as connection:
            value = connection.execute(text("""
                SELECT EXTRACT(EPOCH FROM expires_at)
                FROM rate_limit_counters
                WHERE key_digest = :key AND expires_at > now()
            """), {"key": self._key(key)}).scalar()
        return float(value) if value is not None else time.time()

    def clear(self, key: str) -> None:
        with self._engine().begin() as connection:
            connection.execute(text("""
                DELETE FROM rate_limit_counters WHERE key_digest = :key
            """), {"key": self._key(key)})

    def reset(self) -> int:
        with self._engine().begin() as connection:
            return int(connection.execute(
                text("DELETE FROM rate_limit_counters RETURNING key_digest")
            ).rowcount)

    def check(self) -> bool:
        with self._engine().connect() as connection:
            connection.execute(text("SELECT 1 FROM rate_limit_counters LIMIT 1"))
        return True
