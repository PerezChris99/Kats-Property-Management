"""Public contact and demo inquiries."""
from alembic import op
import sqlalchemy as sa
revision="0011_contact"
down_revision="0010_append_only"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("contact_requests",
      sa.Column("id",sa.String(36),primary_key=True),
      sa.Column("full_name",sa.String(160),nullable=False),
      sa.Column("email",sa.String(254),nullable=False),
      sa.Column("phone",sa.String(30)),
      sa.Column("subject",sa.String(120),nullable=False),
      sa.Column("message",sa.Text(),nullable=False),
      sa.Column("consent",sa.Boolean(),nullable=False),
      sa.Column("status",sa.String(20),nullable=False),
      sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
      sa.Column("reviewed_by",sa.String(36),sa.ForeignKey("users.id",ondelete="RESTRICT")),
      sa.Column("reviewed_at",sa.DateTime(timezone=True)))
    op.create_index("ix_contact_status_created","contact_requests",["status","created_at"])
def downgrade():
    op.drop_table("contact_requests")
