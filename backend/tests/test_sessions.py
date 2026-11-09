from conftest import create_user, auth_client, csrf
from app.models import RefreshSession
from app.extensions import db

def test_login_refresh_rotation_and_logout_revokes_access(app):
    user = create_user("login-sec@kats.test", "OWNER")
    client = app.test_client()
    creds = {"email": "login-sec@kats.test", "password": "ValidPassword123!"}
    login = client.post("/api/v1/auth/login", json=creds)
    assert login.status_code == 200, login.json
    assert client.get("/api/v1/auth/me").status_code == 200
    saved_refresh = client.get_cookie("refresh_token_cookie", path="/api/v1/auth").value
    refreshed = client.post("/api/v1/auth/refresh", headers={
        "X-CSRF-TOKEN": client.get_cookie("csrf_refresh_token").value
    })
    assert refreshed.status_code == 200, refreshed.json
    # Reusing a copied old token is prohibited even if it has not expired.
    replay = app.test_client()
    replay.set_cookie("refresh_token_cookie", saved_refresh, path="/api/v1/auth")
    from flask_jwt_extended import decode_token
    # Deliberately supply original valid CSRF extracted from token claims.
    csrf_refresh = decode_token(saved_refresh)["csrf"]
    reused = replay.post("/api/v1/auth/refresh", headers={"X-CSRF-TOKEN": csrf_refresh})
    assert reused.status_code == 401
    access = client.get_cookie("access_token_cookie").value
    logout = client.post("/api/v1/auth/logout", headers=csrf(client))
    assert logout.status_code == 200, logout.json
    copied = app.test_client()
    copied.set_cookie("access_token_cookie", access)
    assert copied.get("/api/v1/auth/me").status_code == 401
    assert db.session.query(RefreshSession).filter_by(user_id=user.id, revoked_at=None).count() == 0

def test_password_change_invalidates_session(app):
    user = create_user("pw-sec@kats.test", "OWNER")
    cli = app.test_client()
    assert cli.post("/api/v1/auth/login", json={"email":user.email,"password":"ValidPassword123!"}).status_code == 200
    changed = cli.post("/api/v1/auth/change-password",headers=csrf(cli),json={
        "current_password":"ValidPassword123!","new_password":"AnotherLongPass123!"
    })
    assert changed.status_code == 200, changed.json
    assert cli.post("/api/v1/auth/login",json={
        "email":user.email,"password":"ValidPassword123!"
    }).status_code == 401
    assert cli.post("/api/v1/auth/login",json={
        "email":user.email,"password":"AnotherLongPass123!"
    }).status_code == 200

def test_disabled_account_rejects_token(app):
    owner = create_user("owner-admin@kats.test", "OWNER")
    staff = create_user("locked@kats.test", "TENANT")
    admin = auth_client(app, owner)
    user = auth_client(app, staff)
    assert user.get("/api/v1/auth/me").status_code == 200
    result = admin.post("/api/v1/admin/users/"+staff.id+"/status",headers=csrf(admin),json={"is_active":False})
    assert result.status_code == 200
    assert user.get("/api/v1/auth/me").status_code in (401,403)
