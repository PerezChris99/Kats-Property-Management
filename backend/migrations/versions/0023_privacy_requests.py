"""Audited personal data request and manual retention-decision register."""
from alembic import op
import sqlalchemy as sa
revision="0023_privacy_requests"
down_revision="0022_mfa_accounts"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("privacy_requests",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("requester_user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("tenant_id",sa.String(36),sa.ForeignKey("tenants.id",ondelete="RESTRICT")),
        sa.Column("kind",sa.String(25),nullable=False),
        sa.Column("details",sa.Text,nullable=False),
        sa.Column("status",sa.String(25),nullable=False),
        sa.Column("decision_notes",sa.Text),
        sa.Column("reviewed_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("reviewed_at",sa.DateTime(timezone=True)),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("kind IN ('ACCESS','RECTIFY','ERASURE','RESTRICT','OBJECT')",name="ck_privacy_request_kind"),
        sa.CheckConstraint("status IN ('SUBMITTED','IN_REVIEW','COMPLETED','DECLINED')",name="ck_privacy_request_state"))
    op.create_index("ix_privacy_requests_requester_user_id","privacy_requests",["requester_user_id"])
    op.create_index("ix_privacy_requests_status_created","privacy_requests",["status","created_at"])

def downgrade():
    op.drop_index("ix_privacy_requests_status_created",table_name="privacy_requests")
    op.drop_index("ix_privacy_requests_requester_user_id",table_name="privacy_requests")
    op.drop_table("privacy_requests")
