"""Encrypted two-factor authenticator metadata for staff and owners."""
from alembic import op
import sqlalchemy as sa
revision="0022_mfa_accounts"
down_revision="0021_document_scan"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("users",sa.Column("mfa_secret_encrypted",sa.String(512),nullable=True))
    op.add_column("users",sa.Column("mfa_enabled",sa.Boolean,nullable=False,server_default=sa.false()))
    op.add_column("users",sa.Column("mfa_last_step",sa.BigInteger,nullable=True))

def downgrade():
    op.drop_column("users","mfa_last_step")
    op.drop_column("users","mfa_enabled")
    op.drop_column("users","mfa_secret_encrypted")
