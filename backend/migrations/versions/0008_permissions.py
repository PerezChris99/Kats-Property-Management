"""Database-managed endpoint permission matrix."""
from alembic import op
import sqlalchemy as sa
revision = "0008_permissions"
down_revision = "0007_lease_deposits"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("roles",sa.Column("name",sa.String(30),primary_key=True),
                    sa.Column("description",sa.String(250),nullable=False))
    op.create_table("permissions",sa.Column("name",sa.String(160),primary_key=True),
                    sa.Column("description",sa.String(250),nullable=False))
    op.create_table("role_permissions",
        sa.Column("role_name",sa.String(30),sa.ForeignKey("roles.name",ondelete="CASCADE"),primary_key=True),
        sa.Column("permission_name",sa.String(160),sa.ForeignKey("permissions.name",ondelete="CASCADE"),primary_key=True),
        sa.Column("granted_at",sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
