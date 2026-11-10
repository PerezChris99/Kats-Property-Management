"""Access requests are queued for owner approval; no public account is created."""
from app.extensions import db
from app.extra_models import ContactRequest
from app.models import User
from conftest import auth_client, create_user, csrf


def payload(**updates):
    data = {
        "full_name": "Test Property Manager",
        "email": "request@example.invalid",
        "phone": "+256700000001",
        "subject": "ACCESS",
        "message": "Role: Manager\\nPortfolio: Kampala\\nI manage a rental block.",
        "consent": True,
        "website": "",
    }
    return {**data, **updates}


def test_public_access_request_does_not_create_user_and_is_reviewable(client, app):
    submitted = client.post("/api/v1/public/access-requests", json=payload())
    assert submitted.status_code == 201, submitted.json
    assert "No account has been created" in submitted.json["message"]
    assert db.session.query(User).count() == 0
    record = db.session.query(ContactRequest).one()
    assert record.subject == "ACCESS" and record.status == "NEW"
    assert record.email == "request@example.invalid"
    owner = create_user("owner@test.invalid", "OWNER")
    admin = auth_client(app, owner)
    inbox = admin.get("/api/v1/admin/contact-requests")
    assert inbox.status_code == 200
    assert any(item["subject"] == "ACCESS" for item in inbox.json["items"])
    reviewed = admin.post("/api/v1/admin/contact-requests/" + record.id + "/resolve",
                          json={"status": "IN_PROGRESS"}, headers=csrf(admin))
    assert reviewed.status_code == 200
    assert db.session.query(User).count() == 1


def test_access_request_requires_valid_consent_and_message(client):
    for updates in ({"consent": False}, {"message": "short"}, {"email": "bad-email"}):
        response = client.post("/api/v1/public/access-requests", json=payload(**updates))
        assert response.status_code == 400
    assert db.session.query(ContactRequest).count() == 0


def test_access_honeypot_does_not_store_record(client):
    response = client.post("/api/v1/public/access-requests", json=payload(website="spam.example"))
    assert response.status_code == 202
    assert db.session.query(ContactRequest).count() == 0


def test_legacy_contact_url_remains_compatible(client):
    response = client.post("/api/v1/public/contact-requests", json=payload(subject="DEMO"))
    assert response.status_code == 201
    assert db.session.query(ContactRequest).one().subject == "DEMO"
