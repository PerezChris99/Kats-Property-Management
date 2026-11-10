"""Require scanned immutable object versions before signed document downloads."""
from alembic import op
import sqlalchemy as sa
revision="0021_document_scan"
down_revision="0020_utility_meters"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("documents",sa.Column("object_version_id",sa.String(300),nullable=True))
    op.add_column("documents",sa.Column("scan_completed_at",sa.DateTime(timezone=True),nullable=True))

def downgrade():
    op.drop_column("documents","scan_completed_at")
    op.drop_column("documents","object_version_id")
