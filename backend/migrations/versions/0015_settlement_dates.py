"""Explicit verified settlement/reversal timestamps; do not invent historical dates."""
from alembic import op
import sqlalchemy as sa
revision="0015_settlement_dates"
down_revision="0014_expenses"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("payments",sa.Column("settled_at",sa.DateTime(timezone=True)))
    op.add_column("payments",sa.Column("reversed_at",sa.DateTime(timezone=True)))
    op.create_index("ix_payment_settled_at","payments",["settled_at"])
def downgrade():
    op.drop_index("ix_payment_settled_at",table_name="payments")
    op.drop_column("payments","reversed_at")
    op.drop_column("payments","settled_at")
