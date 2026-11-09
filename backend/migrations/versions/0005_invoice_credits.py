"""Versioned invoice lines and credit notes."""
from alembic import op
import sqlalchemy as sa
revision = "0005_invoice_credits"
down_revision = "0004_sessions"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("invoices", sa.Column("credit_ugx", sa.BigInteger(), nullable=False, server_default="0"))
    op.drop_constraint("ck_invoice_amounts", "invoices", type_="check")
    op.create_check_constraint("ck_invoice_amounts", "invoices",
        "total_ugx >= 0 AND paid_ugx >= 0 AND credit_ugx >= 0 AND paid_ugx + credit_ugx <= total_ugx")
    op.create_table("invoice_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("charge_type", sa.String(40), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_ugx", sa.BigInteger(), nullable=False),
        sa.Column("amount_ugx", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("quantity > 0 AND quantity <= 100000 AND unit_price_ugx >= 0 AND amount_ugx >= 0",
                           name="ck_invoice_line_amounts"))
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])
    op.create_table("credit_notes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_ugx", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_ugx > 0", name="ck_credit_positive"))
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])

def downgrade():
    op.drop_table("credit_notes")
    op.drop_table("invoice_lines")
    op.drop_constraint("ck_invoice_amounts", "invoices", type_="check")
    op.create_check_constraint("ck_invoice_amounts", "invoices", "total_ugx >= 0 AND paid_ugx >= 0 AND paid_ugx <= total_ugx")
    op.drop_column("invoices", "credit_ugx")
