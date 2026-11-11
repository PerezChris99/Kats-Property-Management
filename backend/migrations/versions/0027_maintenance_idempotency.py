"""Persist per-actor, collision-safe idempotency for maintenance requests.

Nullable unique fingerprints preserve legacy requests and allow safely
replaying explicitly keyed creates after an unreliable network response.
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_maintenance_idempotency"
down_revision = "0026_scope_and_history_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("maintenance_requests",
                  sa.Column("idempotency_key", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_maintenance_idempotency",
                                "maintenance_requests", ["idempotency_key"])


def downgrade():
    op.drop_constraint("uq_maintenance_idempotency",
                       "maintenance_requests", type_="unique")
    op.drop_column("maintenance_requests", "idempotency_key")
