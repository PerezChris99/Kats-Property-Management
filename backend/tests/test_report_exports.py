from datetime import date
from io import BytesIO
from zipfile import ZipFile
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, Payment
from conftest import create_user, auth_client, csrf

def make_records(owner, tenant_user):
    prop=Property(name="Export Property",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="EX1",rent_ugx=260000,status="OCCUPIED")
    tenant=Tenant(full_name="Tenant Export",phone="+256700101010",user_id=tenant_user.id)
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,1,1),rent_ugx=260000)
    db.session.add(lease);db.session.flush()
    invoice=Invoice(invoice_number="KATS-EXPORT",lease_id=lease.id,tenant_id=tenant.id,
                    period_start=date(2026,11,1),period_end=date(2026,11,30),
                    due_date=date(2026,11,9),total_ugx=260000)
    db.session.add(invoice);db.session.flush()
    paid=Payment(invoice_id=invoice.id,amount_ugx=200000,method="CASH",
                 idempotency_key="export-paid",created_by=owner.id,status="RECONCILED")
    db.session.add(paid);invoice.paid_ugx=200000;db.session.commit()
    return tenant.id,invoice.id,paid.id

def test_statement_pdf_and_receipt_pdf_enforce_tenant_object_scope(app):
    owner=create_user("pdf-owner@kats.test","OWNER")
    user=create_user("pdf-tenant@kats.test","TENANT")
    stranger=create_user("pdf-stranger@kats.test","TENANT")
    tenant_id,invoice_id,payment_id=make_records(owner,user)
    cli=auth_client(app,user)
    statement=cli.get("/api/v1/tenants/"+tenant_id+"/statement.pdf")
    assert statement.status_code==200,statement.json
    assert statement.data.startswith(b"%PDF")
    assert statement.headers["Cache-Control"]=="no-store"
    receipt=cli.get("/api/v1/receipts/"+payment_id+".pdf")
    assert receipt.status_code==200
    assert receipt.data.startswith(b"%PDF")
    outsider=auth_client(app,stranger)
    assert outsider.get("/api/v1/tenants/"+tenant_id+"/statement.pdf").status_code==404
    assert outsider.get("/api/v1/receipts/"+payment_id+".pdf").status_code==404

def test_excel_export_is_valid_zip_and_finance_only(app):
    owner=create_user("xlsx-owner@kats.test","OWNER")
    tenant=create_user("xlsx-tenant@kats.test","TENANT")
    make_records(owner,tenant)
    cli=auth_client(app,owner)
    export=cli.get("/api/v1/reports/export/invoices.xlsx")
    assert export.status_code==200,export.json
    assert export.data.startswith(b"PK")
    with ZipFile(BytesIO(export.data)) as z:
        assert "xl/workbook.xml" in z.namelist()
    blocked=auth_client(app,tenant)
    assert blocked.get("/api/v1/reports/export/invoices.xlsx").status_code==403
