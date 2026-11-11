"""Runtime-role Flask authentication and tenant-isolation check for local PG demo.

Only invoked by ops/local_postgres_demo.py after verified local seed and grants.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app import create_app

def main():
    app=create_app()
    with app.app_context():
        host={"Host":"127.0.0.1:8000"}
        owner=app.test_client()
        available=owner.get("/api/v1/auth/demo-accounts",
            headers={"Host":"127.0.0.1:8000"},environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
        assert available.status_code==200, (available.status_code, available.json)
        assert available.json.get("enabled") and len(available.json.get("accounts",[]))==31
        response=owner.post("/api/v1/auth/demo-sign-in",
            json={"account":"landlord"},headers={"Host":"127.0.0.1:8000"},
            environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
        assert response.status_code==200,(response.status_code,response.json)
        assert response.json["user"]["role"]=="OWNER"
        assert owner.get("/api/v1/dashboard",headers=host).status_code==200
        tenant=app.test_client()
        response=tenant.post("/api/v1/auth/demo-sign-in",
            json={"account":"tenant-01"},headers={"Host":"127.0.0.1:8000"},
            environ_overrides={"REMOTE_ADDR":"127.0.0.1"})
        assert response.status_code==200,(response.status_code,response.json)
        assert response.json["user"]["role"]=="TENANT"
        invoices=tenant.get("/api/v1/invoices",headers=host)
        assert invoices.status_code==200,(invoices.status_code,invoices.json)
        assert len(invoices.json["items"])==2
        assert tenant.get("/api/v1/properties",headers=host).status_code==403
    print("[PASS] PostgreSQL landlord/tenant cookie login, scoped invoices and RBAC",flush=True)

if __name__=="__main__":
    main()
