"""Real preview data tests without modifying the developer's .local database."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from app.extensions import db
from app.models import User, Tenant, Lease, Property, Room, Invoice, Payment, MaintenanceRequest


def load_seeder():
    path = Path(__file__).resolve().parents[2] / "ops" / "seed_demo_preview.py"
    spec = spec_from_file_location("kats_demo_seed_test_module", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_creates_complete_synthetic_landlord_tenant_workflows(app, monkeypatch):
    seed = load_seeder()
    # Test-only injection keeps the real seeder's strict local-preview DB guard intact.
    monkeypatch.setattr(seed, "assert_preview_database", lambda *args: None)
    monkeypatch.setattr(seed, "create_app", lambda: app)
    seed.seed()
    assert db.session.query(User).count() == 31
    assert db.session.query(User).filter_by(role="OWNER").count() == 1
    assert db.session.query(User).filter_by(role="TENANT").count() == 30
    assert db.session.query(Tenant).count() == 30
    assert db.session.query(Lease).filter_by(status="ACTIVE").count() == 30
    assert db.session.query(Property).count() == 3
    assert db.session.query(Room).count() == 33
    assert db.session.query(Room).filter_by(status="OCCUPIED").count() == 30
    assert db.session.query(Room).filter_by(status="VACANT").count() == 3
    assert db.session.query(Invoice).count() == 60
    assert db.session.query(Payment).count() > 0
    assert db.session.query(MaintenanceRequest).count() > 0
    assert all(t.user_id is not None for t in db.session.query(Tenant).all())
    count = db.session.query(Invoice).count()
    seed.seed()
    assert db.session.query(Invoice).count() == count


def test_demo_auth_not_available_in_tests_or_without_preview_guard(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("KATS_PREVIEW_MODE", "1")
    response = client.get("/api/v1/auth/demo-accounts")
    assert response.status_code == 404
    response = client.post("/api/v1/auth/demo-sign-in", json={"account": "landlord"})
    assert response.status_code == 404


def test_demo_accounts_sign_in_through_normal_sessions(app, monkeypatch):
    seed = load_seeder()
    monkeypatch.setattr(seed, "assert_preview_database", lambda *args: None)
    monkeypatch.setattr(seed, "create_app", lambda: app)
    seed.seed()
    # Intentionally replace the preview guard in this test only. The separate
    # negative test proves that the real preview guard rejects test databases.
    monkeypatch.setattr("app.demo_preview.demo_http_allowed", lambda: True)
    landlord = app.test_client()
    options = landlord.get("/api/v1/auth/demo-accounts")
    assert options.status_code == 200
    accounts = options.json["accounts"]
    assert len(accounts) == 31
    assert len([a for a in accounts if a["role"] == "TENANT"]) == 30
    result = landlord.post("/api/v1/auth/demo-sign-in", json={"account": "landlord"})
    assert result.status_code == 200
    assert result.json["user"]["role"] == "OWNER"
    assert landlord.get("/api/v1/auth/me").status_code == 200
    owner_summary = landlord.get("/api/v1/dashboard")
    assert owner_summary.status_code == 200
    assert owner_summary.json["occupied_rooms"] == 30
    assert owner_summary.json["expected_ugx"] > 0
    tenant = app.test_client()
    result = tenant.post("/api/v1/auth/demo-sign-in", json={"account": "tenant-07"})
    assert result.status_code == 200
    assert result.json["user"]["role"] == "TENANT"
    assert tenant.get("/api/v1/tenant/dashboard").json["invoices"] == 2
    assert tenant.get("/api/v1/tenant/lease").json["lease"]["status"] == "ACTIVE"
    personal_invoices = tenant.get("/api/v1/invoices")
    assert personal_invoices.status_code == 200
    assert len(personal_invoices.json["items"]) == 2
    assert tenant.get("/api/v1/properties").status_code == 403
    assert landlord.get("/api/v1/tenant/dashboard").status_code == 403
    assert tenant.post("/api/v1/auth/demo-sign-in", json={"account": "tenant-99"}).status_code == 400


def test_preview_guard_requires_exact_database_and_development_flags(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from app import demo_preview
    file = tmp_path / "kats-preview.sqlite3"
    file.touch()
    monkeypatch.setattr(demo_preview, "EXPECTED", file)
    uri = "sqlite:///" + file.resolve().as_posix()
    candidate = SimpleNamespace(config={"SQLALCHEMY_DATABASE_URI": uri, "TESTING": False})
    monkeypatch.setenv("DATABASE_URL", uri)
    monkeypatch.setenv("KATS_PREVIEW_MODE", "1")
    monkeypatch.setenv("APP_ENV", "development")
    assert demo_preview.demo_preview_enabled(candidate)
    candidate.config["TESTING"] = True
    assert not demo_preview.demo_preview_enabled(candidate)
    candidate.config["TESTING"] = False
    monkeypatch.setenv("APP_ENV", "production")
    assert not demo_preview.demo_preview_enabled(candidate)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/test")
    assert not demo_preview.demo_preview_enabled(candidate)
    monkeypatch.setenv("DATABASE_URL", uri)
    monkeypatch.setenv("KATS_PREVIEW_MODE", "0")
    assert not demo_preview.demo_preview_enabled(candidate)


def test_partial_demo_accounts_are_not_overwritten(app, monkeypatch):
    import pytest
    from argon2 import PasswordHasher
    seed = load_seeder()
    monkeypatch.setattr(seed, "assert_preview_database", lambda *args: None)
    monkeypatch.setattr(seed, "create_app", lambda: app)
    db.session.add(User(
        email="landlord@demo.kats.invalid", full_name="Modified landlord",
        password_hash=PasswordHasher().hash("NotAnActualDemoPassword123!"),
        role="OWNER",
    ))
    db.session.commit()
    with pytest.raises(RuntimeError, match="Partial demo accounts"):
        seed.seed()
    assert db.session.query(User).count() == 1
    assert db.session.query(Property).count() == 0
