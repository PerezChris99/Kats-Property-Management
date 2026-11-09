import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, Index, text
from .extensions import db

def new_id():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="TENANT")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    session_version = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class Property(db.Model):
    __tablename__ = "properties"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(400), nullable=False)
    district = db.Column(db.String(120), nullable=False, default="Kampala")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    property_id = db.Column(db.String(36), db.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True)
    number = db.Column(db.String(60), nullable=False)
    floor_id = db.Column(db.String(36), db.ForeignKey("floors.id", ondelete="RESTRICT"), nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="VACANT")
    rent_ugx = db.Column(db.BigInteger, nullable=False)
    deposit_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    __table_args__ = (
        db.UniqueConstraint("property_id", "number", name="uq_property_room"),
        CheckConstraint("rent_ugx >= 0 AND deposit_ugx >= 0", name="ck_room_amounts"),
    )

class RoomStateHistory(db.Model):
    __tablename__ = "room_state_history"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    old_status = db.Column(db.String(30), nullable=False)
    new_status = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class Tenant(db.Model):
    __tablename__ = "tenants"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    full_name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(254))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class Lease(db.Model):
    __tablename__ = "leases"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    tenant_id = db.Column(db.String(36), db.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    rent_ugx = db.Column(db.BigInteger, nullable=False)
    deposit_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    due_day = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(30), nullable=False, default="ACTIVE")
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ck_lease_dates"),
        CheckConstraint("rent_ugx >= 0 AND deposit_ugx >= 0 AND due_day BETWEEN 1 AND 28", name="ck_lease_terms"),
        Index("uq_active_lease_per_room", "room_id", unique=True,
              postgresql_where=text("status = 'ACTIVE'"), sqlite_where=text("status = 'ACTIVE'")),
    )

class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    invoice_number = db.Column(db.String(70), nullable=False, unique=True)
    lease_id = db.Column(db.String(36), db.ForeignKey("leases.id", ondelete="RESTRICT"), nullable=False, index=True)
    tenant_id = db.Column(db.String(36), db.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    total_ugx = db.Column(db.BigInteger, nullable=False)
    paid_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    credit_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="ISSUED")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint("lease_id", "period_start", "period_end", name="uq_lease_billing_period"),
        CheckConstraint("total_ugx >= 0 AND paid_ugx >= 0 AND credit_ugx >= 0 AND paid_ugx + credit_ugx <= total_ugx", name="ck_invoice_amounts"),
        CheckConstraint("period_end >= period_start", name="ck_invoice_period"),
    )

class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    invoice_id = db.Column(db.String(36), db.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_ugx = db.Column(db.BigInteger, nullable=False)
    method = db.Column(db.String(25), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="PENDING_REVIEW")
    reference = db.Column(db.String(160), unique=True, nullable=True)
    idempotency_key = db.Column(db.String(128), nullable=False, unique=True)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("amount_ugx > 0", name="ck_payment_positive"),)

class LedgerEntry(db.Model):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("uq_ledger_payment_event","payment_id","event",unique=True,
              postgresql_where=text("payment_id IS NOT NULL"),
              sqlite_where=text("payment_id IS NOT NULL")),
    )
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    invoice_id = db.Column(db.String(36), db.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    payment_id = db.Column(db.String(36), db.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=True)
    event = db.Column(db.String(40), nullable=False)
    amount_ugx = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    tenant_id = db.Column(db.String(36), db.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="MEDIUM")
    status = db.Column(db.String(30), nullable=False, default="OPEN")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    property_id = db.Column(db.String(36), db.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    amount_ugx = db.Column(db.BigInteger, nullable=False)
    incurred_on = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    __table_args__ = (CheckConstraint("amount_ugx >= 0", name="ck_expense_nonnegative"),)

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(60), nullable=False)
    target_id = db.Column(db.String(36), nullable=False)
    details = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class CaretakerAssignment(db.Model):
    __tablename__ = "caretaker_assignments"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    caretaker_user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"),
                                  nullable=False, index=True)
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"),
                        nullable=False, index=True)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint("caretaker_user_id", "room_id", name="uq_caretaker_assigned_room"),
    )


class Inspection(db.Model):
    __tablename__ = "inspections"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    lease_id = db.Column(db.String(36), db.ForeignKey("leases.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = db.Column(db.String(36), db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    inspector_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    condition_notes = db.Column(db.Text, nullable=False)
    damage_estimate_ugx = db.Column(db.BigInteger, nullable=False, default=0)
    observed_on = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("damage_estimate_ugx >= 0", name="ck_inspection_damage"),
        CheckConstraint("kind IN ('MOVE_IN','MOVE_OUT','ROUTINE')", name="ck_inspection_kind"),
    )


class RefreshSession(db.Model):
    __tablename__ = "refresh_sessions"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class InvoiceLine(db.Model):
    __tablename__ = "invoice_lines"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    invoice_id = db.Column(db.String(36), db.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    description = db.Column(db.String(300), nullable=False)
    charge_type = db.Column(db.String(40), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price_ugx = db.Column(db.BigInteger, nullable=False)
    amount_ugx = db.Column(db.BigInteger, nullable=False)
    __table_args__ = (CheckConstraint(
        "quantity > 0 AND quantity <= 100000 AND unit_price_ugx >= 0 AND amount_ugx >= 0",
        name="ck_invoice_line_amounts"),)

class CreditNote(db.Model):
    __tablename__ = "credit_notes"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    invoice_id = db.Column(db.String(36), db.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount_ugx = db.Column(db.BigInteger, nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    idempotency_key = db.Column(db.String(128), unique=True, nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("amount_ugx > 0", name="ck_credit_positive"),)


class LeaseAmendment(db.Model):
    __tablename__ = "lease_amendments"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    lease_id = db.Column(db.String(36), db.ForeignKey("leases.id", ondelete="RESTRICT"), nullable=False, index=True)
    previous_end_date = db.Column(db.Date, nullable=False)
    new_end_date = db.Column(db.Date, nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    previous_rent_ugx = db.Column(db.BigInteger, nullable=False)
    new_rent_ugx = db.Column(db.BigInteger, nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("new_end_date > previous_end_date", name="ck_renewal_dates"),
        CheckConstraint("previous_rent_ugx > 0 AND new_rent_ugx > 0", name="ck_renewal_rent"),
    )

class DepositMovement(db.Model):
    __tablename__ = "deposit_movements"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    lease_id = db.Column(db.String(36), db.ForeignKey("leases.id", ondelete="RESTRICT"), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False)
    amount_ugx = db.Column(db.BigInteger, nullable=False)
    external_reference = db.Column(db.String(160))
    reason = db.Column(db.String(500), nullable=False)
    idempotency_key = db.Column(db.String(128), nullable=False, unique=True)
    status = db.Column(db.String(30), nullable=False, default="PENDING_REVIEW")
    created_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reviewed_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        db.UniqueConstraint("kind", "external_reference", name="uq_deposit_external_reference"),
        CheckConstraint("amount_ugx > 0", name="ck_deposit_amount"),
        CheckConstraint("kind IN ('HOLD','REFUND','WITHHOLD')", name="ck_deposit_kind"),
        CheckConstraint("status IN ('PENDING_REVIEW','APPROVED','REJECTED')", name="ck_deposit_state"),
    )


class Permission(db.Model):
    __tablename__ = "permissions"
    name = db.Column(db.String(160), primary_key=True)
    description = db.Column(db.String(250), nullable=False, default="")

class Role(db.Model):
    __tablename__ = "roles"
    name = db.Column(db.String(30), primary_key=True)
    description = db.Column(db.String(250), nullable=False, default="")

class RolePermission(db.Model):
    __tablename__ = "role_permissions"
    role_name = db.Column(db.String(30), db.ForeignKey("roles.name", ondelete="CASCADE"), primary_key=True)
    permission_name = db.Column(db.String(160), db.ForeignKey("permissions.name", ondelete="CASCADE"), primary_key=True)
    granted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class Building(db.Model):
    __tablename__ = "buildings"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    property_id = db.Column(db.String(36), db.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint("property_id", "name", name="uq_property_building_name"),)

class Floor(db.Model):
    __tablename__ = "floors"
    id = db.Column(db.String(36), primary_key=True, default=new_id)
    building_id = db.Column(db.String(36), db.ForeignKey("buildings.id", ondelete="RESTRICT"), nullable=False, index=True)
    level = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint("building_id", "level", name="uq_building_floor_level"),
        CheckConstraint("level BETWEEN -10 AND 300", name="ck_floor_level"),
    )
