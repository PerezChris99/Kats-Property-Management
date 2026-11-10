"""Monthly billing must batch reads without compromising rent safeguards."""
from datetime import date
from sqlalchemy import event
from app.extensions import db
from app.models import (Property, Room, Tenant, Lease, LeaseAmendment,
                        Invoice, InvoiceLine)
from app.billing import generate_monthly_rent
from conftest import create_user


def test_many_leases_have_bounded_billing_selects_and_correct_effective_rent(app):
    owner = create_user("batch-rent-owner@kats.test", "OWNER")
    property_ = Property(name="Large Building", address="Kampala", district="Kampala")
    db.session.add(property_)
    db.session.flush()
    leases = []
    for index in range(35):
        room = Room(property_id=property_.id, number=f"UNIT-{index:03d}",
                    rent_ugx=200000, status="OCCUPIED")
        tenant = Tenant(full_name=f"Occupant {index}", phone=f"+256700{index:06d}")
        db.session.add_all([room, tenant])
        db.session.flush()
        lease = Lease(room_id=room.id, tenant_id=tenant.id,
                      start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
                      rent_ugx=200000)
        db.session.add(lease)
        leases.append(lease)
    db.session.flush()

    # Past amendment must change the rate; a midmonth amendment must NOT
    # silently bill either of the rates without finance proration.
    for index, effective in ((0, date(2026, 10, 1)), (1, date(2026, 11, 16))):
        db.session.add(LeaseAmendment(
            lease_id=leases[index].id, previous_end_date=date(2026, 12, 31),
            new_end_date=date(2027, 12, 31), effective_date=effective,
            previous_rent_ugx=200000, new_rent_ugx=230000, reason="Approved",
            created_by=owner.id
        ))
    # Existing manual partial rent must block automatic November rent.
    partial = Invoice(lease_id=leases[2].id, tenant_id=leases[2].tenant_id,
                      invoice_number="KATS-BATCH-PARTIAL",
                      period_start=date(2026, 11, 1), period_end=date(2026, 11, 20),
                      due_date=date(2026, 11, 5), total_ugx=130000)
    db.session.add(partial)
    db.session.flush()
    db.session.add(InvoiceLine(
        invoice_id=partial.id, description="Approved partial-period rent",
        charge_type="RENT", quantity=1, unit_price_ugx=130000, amount_ugx=130000))
    db.session.commit()

    reads = []
    def inspect(_connection, _cursor, statement, _params, _context, _executemany):
        query = " ".join(statement.lower().split())
        if query.startswith("select") and any(
            token in query for token in ("from lease_amendments", "from invoices")
        ):
            reads.append(query)

    event.listen(db.engine, "before_cursor_execute", inspect)
    try:
        result = generate_monthly_rent(date(2026, 11, 10), owner)
    finally:
        event.remove(db.engine, "before_cursor_execute", inspect)
    assert result["issued"] == 33, result
    assert result["requires_manual_proration_review"] == 2, result
    assert len(reads) <= 5, f"N+1 billing SELECT regression: {len(reads)}"
    rent = db.session.query(Invoice).filter_by(lease_id=leases[0].id).one()
    assert rent.total_ugx == 230000
    assert db.session.query(Invoice).count() == 34
    retry = generate_monthly_rent(date(2026, 11, 10), owner)
    assert retry["issued"] == 0 and retry["already_exists"] == 33
    assert retry["requires_manual_proration_review"] == 2
