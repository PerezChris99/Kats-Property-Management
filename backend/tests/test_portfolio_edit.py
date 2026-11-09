from datetime import date
from app.extensions import db
from app.models import Property,Building,Floor,Room,Tenant,Lease,AuditLog
from conftest import create_user,auth_client,csrf

def test_portfolio_editing_preserves_signed_leases_and_audits_changes(app):
    owner=create_user("edit-owner@kats.test","OWNER")
    tenant_user=create_user("edit-tenant@kats.test","TENANT")
    p=Property(name="Old name",address="Old address",district="Kampala")
    db.session.add(p);db.session.flush()
    building=Building(property_id=p.id,name="Original tower")
    db.session.add(building);db.session.flush()
    floor=Floor(building_id=building.id,level=0,label="Ground")
    db.session.add(floor);db.session.flush()
    room=Room(property_id=p.id,floor_id=floor.id,number="A-1",rent_ugx=100000,deposit_ugx=50000,status="OCCUPIED")
    tenant=Tenant(full_name="Renter",phone="+256700000333")
    db.session.add_all([room,tenant]);db.session.flush()
    lease=Lease(tenant_id=tenant.id,room_id=room.id,
                start_date=date(2026,1,1),end_date=date(2027,1,1),
                rent_ugx=100000,deposit_ugx=50000)
    db.session.add(lease);db.session.commit()
    admin=auth_client(app,owner)
    pupdate=admin.put("/api/v1/properties/"+p.id,json={"name":"New name","address":"Verified street"},
        headers=csrf(admin))
    assert pupdate.status_code==200,pupdate.json
    bu=admin.put("/api/v1/buildings/"+building.id,json={"name":"North tower"},
        headers=csrf(admin))
    assert bu.status_code==200,bu.json
    fu=admin.put("/api/v1/floors/"+floor.id,json={"level":-1,"label":"Basement"},
        headers=csrf(admin))
    assert fu.status_code==200,fu.json
    ru=admin.put("/api/v1/rooms/"+room.id+"/details",json={
        "number":"B-1","rent_ugx":120000,"deposit_ugx":70000
    },headers=csrf(admin))
    assert ru.status_code==200,ru.json
    assert db.session.get(Lease,lease.id).rent_ugx==100000
    assert db.session.get(Lease,lease.id).deposit_ugx==50000
    assert admin.get("/api/v1/rooms?q=B-1").json["total"]==1
    assert admin.get("/api/v1/rooms?q=A-1").json["total"]==0
    assert admin.get("/api/v1/buildings?q=North").json["total"]==1
    assert admin.get("/api/v1/floors?q=Base").json["total"]==1
    assert admin.get("/api/v1/properties?q=Verified").json["total"]==1
    assert db.session.query(AuditLog).filter(
        AuditLog.action.in_(("property.update","building.update","floor.update","room.details_update"))).count()==4
    outsider=auth_client(app,tenant_user)
    assert outsider.put("/api/v1/properties/"+p.id,json={"name":"Unauthorized"},
        headers=csrf(outsider)).status_code==403
