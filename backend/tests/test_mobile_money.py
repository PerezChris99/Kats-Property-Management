from datetime import date
from app.extensions import db
from app.models import Property, Room, Tenant, Lease, Invoice, Payment, LedgerEntry
from app.extra_models import ProviderAttempt
from app.providers import VerifiedStatus, ProviderError, MTNClient
from conftest import create_user, auth_client, csrf

def invoice_seed(tenant_user=None):
    prop=Property(name="Mobile",address="Kampala",district="Kampala")
    db.session.add(prop);db.session.flush()
    room=Room(property_id=prop.id,number="MM1",rent_ugx=250000,status="OCCUPIED")
    tenant=Tenant(full_name="Mobile tenant",phone="+256772000000",
                  user_id=tenant_user.id if tenant_user else None)
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(room_id=room.id,tenant_id=tenant.id,start_date=date(2026,1,1),
                end_date=date(2027,1,1),rent_ugx=250000)
    db.session.add(lease);db.session.flush()
    invoice=Invoice(invoice_number="KATS-MOBILE-UNIT",tenant_id=tenant.id,lease_id=lease.id,
                    period_start=date(2026,11,1),period_end=date(2026,11,30),
                    due_date=date(2026,11,9),total_ugx=250000)
    db.session.add(invoice);db.session.commit()
    return invoice.id

def test_mobile_payment_disabled_fails_closed(app):
    user=create_user("mobile-owner@kats.test","OWNER")
    id=invoice_seed()
    client=auth_client(app,user)
    res=client.post("/api/v1/payments/mobile/initiate",headers=csrf(client),json={
        "invoice_id":id,"amount_ugx":100000,"provider":"MTN_MOMO",
        "msisdn":"256772000000","idempotency_key":"mobile-disabled"})
    assert res.status_code == 503
    assert db.session.query(Payment).count() == 0

def test_mobile_collection_only_posts_after_verified_provider_status(app,monkeypatch):
    user=create_user("mobile-owner-2@kats.test","OWNER")
    inv_id=invoice_seed()
    import app.mobile_payments as mobile
    import app.settlement as settlement
    monkeypatch.setenv("MTN_MOMO_ENABLED","true")
    class Fake:
        def initiate(self,reference,amount,msisdn,invoice_number):
            assert amount==70000 and msisdn=="256772000000"
        def status(self,reference,amount):
            return VerifiedStatus("SUCCESSFUL",transaction_id="MTN-VERIFIED-0001")
    monkeypatch.setattr(mobile,"provider",lambda name:Fake())
    monkeypatch.setattr(settlement,"provider",lambda name:Fake())
    client=auth_client(app,user)
    request={"invoice_id":inv_id,"amount_ugx":70000,"provider":"MTN_MOMO",
             "msisdn":"256772000000","idempotency_key":"mobile-v1"}
    start=client.post("/api/v1/payments/mobile/initiate",headers=csrf(client),json=request)
    assert start.status_code==202,start.json
    payment_id=start.json["payment"]["id"]
    assert db.session.get(Invoice,inv_id).paid_ugx==0
    duplicate=client.post("/api/v1/payments/mobile/initiate",headers=csrf(client),json=request)
    assert duplicate.status_code==200 and duplicate.json["payment"]["id"]==payment_id
    assert db.session.query(ProviderAttempt).count()==1
    done=client.post("/api/v1/payments/mobile/"+payment_id+"/verify",headers=csrf(client))
    assert done.status_code==200,done.json
    assert done.json["result"]["state"]=="RECONCILED"
    assert db.session.get(Invoice,inv_id).paid_ugx==70000
    assert db.session.query(LedgerEntry).filter_by(payment_id=payment_id).count()==1
    again=client.post("/api/v1/payments/mobile/"+payment_id+"/verify",headers=csrf(client))
    assert again.status_code==200 and again.json["result"]["state"]=="RECONCILED"
    assert db.session.query(LedgerEntry).filter_by(payment_id=payment_id).count()==1

def test_unverified_provider_state_never_credits_money(app,monkeypatch):
    user=create_user("unverified-owner@kats.test","OWNER")
    inv_id=invoice_seed()
    payment=Payment(invoice_id=inv_id,amount_ugx=50000,method="MTN_MOMO",
                    status="PENDING_PROVIDER",idempotency_key="bad-mobile",created_by=user.id)
    db.session.add(payment);db.session.flush()
    db.session.add(ProviderAttempt(payment_id=payment.id,provider="MTN_MOMO",
        reference="f2ea9b95-bd74-4485-b797-e36a9d78fe26",requested_amount_ugx=50000,msisdn="256772000000"))
    db.session.commit()
    import app.settlement as settle
    monkeypatch.setattr(settle,"provider",lambda name:type("Fake",(),{
        "status":lambda self,reference,amount:VerifiedStatus("UNVERIFIED",reason="mismatched fields")
    })())
    outcome=settle.verify_and_post(payment.id)
    assert outcome["credited"] is False
    assert db.session.get(Invoice,inv_id).paid_ugx==0
    assert db.session.query(LedgerEntry).count()==0

def test_mtn_status_reconciles_amount_and_currency(monkeypatch):
    monkeypatch.setenv("MTN_MOMO_BASE_URL","https://sandbox.momodeveloper.mtn.com")
    monkeypatch.setenv("MTN_MOMO_API_USER","sandbox-user")
    monkeypatch.setenv("MTN_MOMO_API_KEY","sandbox-api-key")
    monkeypatch.setenv("MTN_MOMO_SUBSCRIPTION_KEY","sandbox-subscription")
    monkeypatch.setenv("MTN_MOMO_TARGET_ENVIRONMENT","sandbox")
    client=MTNClient()
    monkeypatch.setattr(client,"headers",lambda:{"Authorization":"Bearer fake"})
    monkeypatch.setattr(client,"request",lambda *args,**kwargs:{
        "status":"SUCCESSFUL","amount":"50000","currency":"USD",
        "externalId":"test","financialTransactionId":"wrong-currency"
    })
    assert client.status("test",50000).state=="UNVERIFIED"
