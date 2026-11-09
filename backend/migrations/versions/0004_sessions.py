"""Session revision and one-time refresh tracking."""
from alembic import op
import sqlalchemy as sa

revision = "0004_sessions"
down_revision = "0003_inspections"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("refresh_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_jti", sa.String(64), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])

def downgrade():
    op.drop_table("refresh_sessions")
    op.drop_column("users", "session_version")
