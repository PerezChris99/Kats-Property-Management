"""Schedule durable exponential retry times for external outbox delivery."""
from alembic import op
import sqlalchemy as sa
revision="0009_outbox_retry"
down_revision="0008_permissions"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("efris_submissions",sa.Column("next_attempt_at",sa.DateTime(timezone=True)))
    op.add_column("notifications",sa.Column("next_attempt_at",sa.DateTime(timezone=True)))
    op.create_index("ix_efris_status_retry","efris_submissions",["state","next_attempt_at"])
    op.create_index("ix_notifications_status_retry","notifications",["status","next_attempt_at"])
def downgrade():
    op.drop_index("ix_notifications_status_retry",table_name="notifications")
    op.drop_index("ix_efris_status_retry",table_name="efris_submissions")
    op.drop_column("notifications","next_attempt_at")
    op.drop_column("efris_submissions","next_attempt_at")
