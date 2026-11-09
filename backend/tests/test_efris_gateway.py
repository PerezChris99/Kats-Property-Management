from datetime import date, datetime, timezone
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, InvoiceLine
from app.extra_models import FiscalSubmission
from app.efris_gateway import FiscalReply, run_fiscal_batch
from conftest import create_user

def seed(approver):
    p=Property(name="Fiscal Court",address="Kampala",district="Kampala")
    db.session.add(p);db.session.flush()
    r=Room(property_id=p.id,number="F1",status="OCCUPIED",rent_ugx=120000)
    t=Tenant(full_name="Fiscal Tenant",phone="+256700043210")
    db.session.add_all([r,t]);db.session.flush()
    l=Lease(room_id=r.id,tenant_id=t.id,start_date=date(2026,1,1),
            end_date=date(2027,1,1),rent_ugx=120000)
    db.session.add(l);db.session.flush()
    i=Invoice(invoice_number="KATS-FISCAL-GW",lease_id=l.id,tenant_id=t.id,
              period_start=date(2026,11,1),period_end=date(2026,11,30),
              due_date=date(2026,11,9),total_ugx=120000)
    db.session.add(i);db.session.flush()
    db.session.add(InvoiceLine(invoice_id=i.id,description="Rent",charge_type="RENT",quantity=1,
                               unit_price_ugx=120000,amount_ugx=120000))
    queue=FiscalSubmission(invoice_id=i.id,document_type="INVOICE",
        idempotency_key="efris-"+i.id,payload={"invoice_number":i.invoice_number},
        state="PENDING_FISCALIZATION")
    db.session.add(queue);db.session.commit()
    return queue.id

def test_efris_gateway_requires_authenticated_complete_ura_proof(app):
    staff=create_user("gateway-staff@kats.test","ACCOUNTANT")
    id=seed(staff)
    class IncompleteGateway:
        def submit_invoice(self, **kwargs):
            return FiscalReply(status="ACCEPTED",fiscal_document_number="FAKE",
                qr_payload="QR",verification_url="http://unsafe.example",authenticated=True)
    first=run_fiscal_batch(adapter=IncompleteGateway(),now=datetime(2026,11,9,tzinfo=timezone.utc))
    assert first["accepted"]==0 and first["processed"]==1
    queued=db.session.get(FiscalSubmission,id)
    assert queued.state=="RETRYING"
    assert queued.fiscal_document_number is None
    class AuthenticatedGateway:
        def submit_invoice(self, **kwargs):
            assert kwargs["idempotency_key"].startswith("efris-")
            return FiscalReply(status="ACCEPTED",fiscal_document_number="URA-VERIFIED-01234",
                qr_payload="official-qr-payload",verification_url="https://verification.ura.go.ug/verify",
                provider_response_id="ura-test-1",authenticated=True)
    processed=run_fiscal_batch(adapter=AuthenticatedGateway(),now=datetime(2026,11,9,0,10,tzinfo=timezone.utc))
    assert processed["accepted"]==1,processed
    assert db.session.get(FiscalSubmission,id).state=="ACCEPTED"

def test_efris_gateway_disabled_fails_closed(app,monkeypatch):
    monkeypatch.setenv("EFRIS_ENABLED","false")
    result=run_fiscal_batch()
    assert result["waiting_for_ura_adapter"] is True
    assert result["accepted"]==0
