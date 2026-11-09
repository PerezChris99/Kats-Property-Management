from conftest import create_user,auth_client,csrf
from app.extensions import db
from app.models import Permission,RolePermission
def test_permission_registry_seed_and_runtime_revocation(app):
    superadmin=create_user("perm-root@kats.test","SUPER_ADMIN")
    manager=create_user("perm-manager@kats.test","MANAGER")
    runner=app.test_cli_runner()
    seeded=runner.invoke(args=["seed-permissions"])
    assert seeded.exit_code==0,seeded.output
    assert db.session.get(Permission,"route:api.properties") is not None
    cli=auth_client(app,manager)
    assert cli.get("/api/v1/properties").status_code==200
    master=auth_client(app,superadmin)
    decision=master.put("/api/v1/admin/permissions/route:api.properties/roles/MANAGER",
        headers=csrf(master),json={"allowed":False})
    assert decision.status_code==200,decision.json
    assert cli.get("/api/v1/properties").status_code==403
    decision=master.put("/api/v1/admin/permissions/route:api.properties/roles/MANAGER",
        headers=csrf(master),json={"allowed":True})
    assert decision.status_code==200
    assert cli.get("/api/v1/properties").status_code==200
    # Only existing decorator-approved roles can receive a grant.
    unauthorized=master.put("/api/v1/admin/permissions/route:api.properties/roles/TENANT",
        headers=csrf(master),json={"allowed":True})
    assert unauthorized.status_code==403
    assert db.session.get(RolePermission,("TENANT","route:api.properties")) is None
