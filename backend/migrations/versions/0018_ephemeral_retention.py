"""Index ephemeral credential expiration for bounded scheduled pruning."""
from alembic import op

revision="0018_ephemeral_retention"
down_revision="0017_document_rls"
branch_labels=None
depends_on=None

def upgrade():
    op.create_index("ix_refresh_sessions_expires_at","refresh_sessions",["expires_at"])
    op.create_index("ix_account_tokens_expires_at","account_tokens",["expires_at"])

def downgrade():
    op.drop_index("ix_account_tokens_expires_at",table_name="account_tokens")
    op.drop_index("ix_refresh_sessions_expires_at",table_name="refresh_sessions")
