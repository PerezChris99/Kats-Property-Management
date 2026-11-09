"""Operational workflow tables: provider attempts, EFRIS, outbox, documents, work orders, legal pages."""
from alembic import op
import sqlalchemy as sa
revision = "0006_operations"
down_revision = "0005_invoice_credits"
branch_labels = None
depends_on = None

def idc():
    return sa.Column("id",sa.String(36),primary_key=True)
def fk(name,ref,optional=False):
    return sa.Column(name,sa.String(36),sa.ForeignKey(ref,ondelete="RESTRICT"),nullable=optional)
def dt(name,nullable=False):
    return sa.Column(name,sa.DateTime(timezone=True),nullable=nullable)
def string(name,length,nullable=False):
    return sa.Column(name,sa.String(length),nullable=nullable)

def upgrade():
    op.create_table("provider_attempts",idc(),fk("payment_id","payments.id"),
        string("provider",20),string("reference",100),
        sa.Column("requested_amount_ugx",sa.BigInteger(),nullable=False),string("msisdn",20),
        string("status",30),sa.Column("verification_attempts",sa.Integer(),nullable=False),
        dt("last_verified_at",True),string("last_error_code",80,True),
        string("last_response_digest",64,True),string("provider_transaction_id",150,True),dt("created_at"),
        sa.UniqueConstraint("payment_id"),sa.UniqueConstraint("reference"),sa.UniqueConstraint("provider_transaction_id"),
        sa.CheckConstraint("requested_amount_ugx > 0",name="ck_provider_amount"))
    op.create_table("efris_submissions",idc(),fk("invoice_id","invoices.id"),
        string("document_type",30),string("idempotency_key",128),
        string("state",30),sa.Column("payload",sa.JSON(),nullable=False),
        sa.Column("accepted_metadata",sa.JSON(),nullable=False),
        string("fiscal_document_number",120,True),string("verification_url",800,True),
        sa.Column("qr_payload",sa.Text()),sa.Column("attempt_count",sa.Integer(),nullable=False),
        string("last_error_code",100,True),dt("created_at"),dt("acknowledged_at",True),
        sa.UniqueConstraint("idempotency_key"),sa.UniqueConstraint("invoice_id","document_type",name="uq_fiscal_document_intent"))
    op.create_index("ix_efris_submissions_invoice_id","efris_submissions",["invoice_id"])
    op.create_table("notifications",idc(),fk("user_id","users.id"),
        string("channel",15),string("kind",80),string("title",200),
        sa.Column("body",sa.Text(),nullable=False),string("status",25),
        string("dedupe_key",160),sa.Column("attempt_count",sa.Integer(),nullable=False),
        string("last_error_code",80,True),dt("created_at"),dt("delivered_at",True),dt("read_at",True),
        sa.UniqueConstraint("dedupe_key"),sa.CheckConstraint("attempt_count >= 0",name="ck_notification_attempts"))
    op.create_index("ix_notifications_user_id","notifications",["user_id"])
    op.create_table("work_orders",idc(),fk("request_id","maintenance_requests.id"),
        fk("assigned_user_id","users.id",True),string("contractor_name",200,True),
        sa.Column("scope",sa.Text(),nullable=False),string("status",30),
        sa.Column("estimated_cost_ugx",sa.BigInteger(),nullable=False),
        sa.Column("actual_cost_ugx",sa.BigInteger(),nullable=False),dt("assigned_at"),dt("completed_at",True),
        sa.CheckConstraint("estimated_cost_ugx >= 0 AND actual_cost_ugx >= 0",name="ck_work_cost"))
    op.create_index("ix_work_orders_request_id","work_orders",["request_id"])
    op.create_table("documents",idc(),fk("owner_user_id","users.id"),
        fk("tenant_id","tenants.id",True),fk("lease_id","leases.id",True),
        fk("room_id","rooms.id",True),string("category",30),
        string("object_key",200),string("filename",255),string("mime_type",100),
        string("status",25),sa.Column("size_bytes",sa.BigInteger()),
        string("checksum_sha256",64,True),dt("created_at"),
        sa.UniqueConstraint("object_key"),
        sa.CheckConstraint("size_bytes IS NULL OR size_bytes BETWEEN 0 AND 8388608",name="ck_document_size"))
    op.create_index("ix_documents_owner_user_id","documents",["owner_user_id"])
    op.create_index("ix_documents_tenant_id","documents",["tenant_id"])
    op.create_table("legal_pages",idc(),string("slug",60),
        sa.Column("version",sa.Integer(),nullable=False),string("title",200),
        sa.Column("content",sa.Text(),nullable=False),sa.Column("published",sa.Boolean(),nullable=False),
        fk("created_by","users.id"),dt("created_at"),
        sa.UniqueConstraint("slug","version",name="uq_legal_version"))
    op.create_table("system_settings",string("key",100),sa.PrimaryKeyConstraint("key"),
        sa.Column("value",sa.JSON(),nullable=False),fk("updated_by","users.id"),dt("updated_at"))

def downgrade():
    for table in ("system_settings","legal_pages","documents","work_orders",
                  "notifications","efris_submissions","provider_attempts"):
        op.drop_table(table)
