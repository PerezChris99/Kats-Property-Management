"""One-time hashed account onboarding and recovery tokens."""
from alembic import op
import sqlalchemy as sa

revision="0013_account_tokens"
down_revision="0012_building_hierarchy"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("account_tokens",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("purpose",sa.String(16),nullable=False),
        sa.Column("digest",sa.String(64),nullable=False,unique=True),
        sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("consumed_at",sa.DateTime(timezone=True)),
        sa.Column("issued_by",sa.String(36),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.CheckConstraint("purpose IN ('INVITE','RESET')",name="ck_account_token_purpose"))
    op.create_index("ix_account_tokens_user_id","account_tokens",["user_id"])
    op.create_index("ix_account_tokens_unused_expiry","account_tokens",["purpose","consumed_at","expires_at"])

def downgrade():
    op.drop_table("account_tokens")
