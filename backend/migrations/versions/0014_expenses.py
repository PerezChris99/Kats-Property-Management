"""Two-person expense authorization and signed append-only expense events."""
from alembic import op
import sqlalchemy as sa
revision="0014_expenses"
down_revision="0013_account_tokens"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("expenses",sa.Column("idempotency_key",sa.String(128)))
    op.add_column("expenses",sa.Column("status",sa.String(24),nullable=False,
                                       server_default="REVIEW_REQUIRED"))
    op.add_column("expenses",sa.Column("reviewed_by",sa.String(36),
                    sa.ForeignKey("users.id",ondelete="RESTRICT")))
    op.add_column("expenses",sa.Column("reviewed_at",sa.DateTime(timezone=True)))
    op.add_column("expenses",sa.Column("reversal_reason",sa.String(500)))
    op.create_unique_constraint("uq_expense_idempotency","expenses",["idempotency_key"])
    op.create_check_constraint("ck_expense_state","expenses",
        "status IN ('PENDING_APPROVAL','REVIEW_REQUIRED','APPROVED','REJECTED','REVERSED')")
    op.create_table("expense_events",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("expense_id",sa.String(36),sa.ForeignKey("expenses.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("event",sa.String(30),nullable=False),
        sa.Column("amount_ugx",sa.BigInteger(),nullable=False),
        sa.Column("actor_id",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("reason",sa.String(500),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("expense_id","event",name="uq_expense_event_once"))
    op.create_index("ix_expense_events_expense_id","expense_events",["expense_id"])
    if op.get_bind().dialect.name=="postgresql":
        op.execute("""CREATE TRIGGER kats_protect_expense_events
          BEFORE UPDATE OR DELETE ON expense_events
          FOR EACH ROW EXECUTE FUNCTION kats_append_only_guard()""")
        op.execute("""CREATE TRIGGER kats_no_delete_expenses
          BEFORE DELETE ON expenses
          FOR EACH ROW EXECUTE FUNCTION kats_append_only_guard()""")
def downgrade():
    if op.get_bind().dialect.name=="postgresql":
        op.execute("DROP TRIGGER kats_no_delete_expenses ON expenses")
        op.execute("DROP TRIGGER kats_protect_expense_events ON expense_events")
    op.drop_table("expense_events")
    op.drop_constraint("ck_expense_state","expenses",type_="check")
    op.drop_constraint("uq_expense_idempotency","expenses",type_="unique")
    op.drop_column("expenses","reversal_reason")
    op.drop_column("expenses","reviewed_at")
    op.drop_column("expenses","reviewed_by")
    op.drop_column("expenses","status")
    op.drop_column("expenses","idempotency_key")
