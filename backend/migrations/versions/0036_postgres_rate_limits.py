"""Add durable, shared rate-limit buckets for Redis-free PostgreSQL deployments.

Revision ID: 0036_postgres_rate_limits
Revises: 0035_bank_statement_guard
"""
import sqlalchemy as sa
from alembic import op

revision = "0036_postgres_rate_limits"
down_revision = "0035_bank_statement_guard"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rate_limit_counters",
        sa.Column("key_digest", sa.String(length=64), primary_key=True),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("hits > 0", name="ck_rate_limit_positive_hits"),
    )
    op.create_index("ix_rate_limit_counters_expires_at", "rate_limit_counters", ["expires_at"])


def downgrade():
    op.drop_index("ix_rate_limit_counters_expires_at", table_name="rate_limit_counters")
    op.drop_table("rate_limit_counters")
