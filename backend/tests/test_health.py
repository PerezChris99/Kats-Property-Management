def test_health(client):
    assert client.get("/healthz").json == {"status": "ok"}
    assert client.get("/readyz").json == {"status": "ready"}
    missing = client.get("/not-real")
    assert missing.status_code == 404
    assert missing.json["error"]["code"] == "NOT_FOUND"

def test_registration_disabled(client):
    response = client.post("/api/v1/auth/register", json={
        "full_name": "Anonymous", "email": "a@example.test", "password": "Verylongpassword!"
    })
    assert response.status_code == 403
