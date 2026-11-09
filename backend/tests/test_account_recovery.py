from urllib.parse import urlparse
from flask_jwt_extended import decode_token
from app.extensions import db
from app.models import User
from app.account_models import AccountToken
from conftest import create_user,auth_client,csrf

def test_invitation_requires_email_and_never_returns_plaintext_token(app,monkeypatch):
    owner=create_user("invite-owner@kats.test","OWNER")
    admin=auth_client(app,owner)
    import app.account_recovery as recovery
    monkeypatch.setattr(recovery,"mail_configured",lambda:False)
    denied=admin.post("/api/v1/admin/invitations",headers=csrf(admin),
        json={"full_name":"Test Tenant","email":"newtenant@kats.test","role":"TENANT"})
    assert denied.status_code==503
    assert db.session.query(User).filter_by(email="newtenant@kats.test").first() is None
    sent=[]
    monkeypatch.setattr(recovery,"mail_configured",lambda:True)
    monkeypatch.setattr(recovery,"send_link",lambda user,purpose,secret:sent.append((user,purpose,secret)))
    created=admin.post("/api/v1/admin/invitations",headers=csrf(admin),
        json={"full_name":"Test Tenant","email":"NEWtenant@kats.test","role":"TENANT"})
    assert created.status_code==201,created.json
    assert created.json["user"]["is_active"] is False
    assert "token" not in created.json and "password" not in created.json
    _,purpose,secret=sent[0]
    assert purpose=="INVITE" and len(secret)>=60
    assert db.session.query(AccountToken).filter_by(digest=recovery.digest(secret)).count()==1
    assert secret not in str(db.session.query(AccountToken).all())
    assert admin.post("/api/v1/admin/invitations",headers=csrf(admin),
        json={"full_name":"Second","email":"newtenant@kats.test","role":"OWNER"}).status_code==403
    user=db.session.query(User).filter_by(email="newtenant@kats.test").one()
    denied_login=app.test_client().post("/api/v1/auth/login",json={
        "email":user.email,"password":"ValidPassword123!"})
    assert denied_login.status_code==401
    activated=app.test_client().post("/api/v1/auth/complete-token",json={
        "token":secret,"new_password":"NewStrongPassword123!"})
    assert activated.status_code==200,activated.json
    assert db.session.get(User,user.id).is_active is True
    assert app.test_client().post("/api/v1/auth/complete-token",json={
        "token":secret,"new_password":"AnotherStrongPassword123!"}).status_code==400
    success=app.test_client().post("/api/v1/auth/login",json={
        "email":"newtenant@kats.test","password":"NewStrongPassword123!"})
    assert success.status_code==200,success.json

def test_reset_is_enumeration_safe_and_revokes_sessions(app,monkeypatch):
    target=create_user("reset-user@kats.test","TENANT")
    import app.account_recovery as recovery
    emails=[]
    monkeypatch.setattr(recovery,"mail_configured",lambda:True)
    monkeypatch.setattr(recovery,"send_link",lambda user,purpose,secret:emails.append((user.email,purpose,secret)))
    real=app.test_client()
    assert real.post("/api/v1/auth/login",json={
        "email":target.email,"password":"ValidPassword123!"}).status_code==200
    old_access=real.get_cookie("access_token_cookie").value
    unknown=app.test_client().post("/api/v1/auth/recover",json={"email":"unknown@kats.test"})
    known=app.test_client().post("/api/v1/auth/recover",json={"email":target.email})
    assert unknown.status_code==known.status_code==202
    assert unknown.json==known.json
    assert len(emails)==1
    _,purpose,secret=emails[0]
    assert purpose=="RESET"
    done=app.test_client().post("/api/v1/auth/complete-token",json={
        "token":secret,"new_password":"MuchBetterPassword123!"})
    assert done.status_code==200,done.json
    stolen=app.test_client()
    stolen.set_cookie("access_token_cookie",old_access)
    assert stolen.get("/api/v1/auth/me").status_code==401
    assert app.test_client().post("/api/v1/auth/login",json={
        "email":target.email,"password":"ValidPassword123!"}).status_code==401
    assert app.test_client().post("/api/v1/auth/login",json={
        "email":target.email,"password":"MuchBetterPassword123!"}).status_code==200

def test_resend_invalidates_previous_invite_and_locks_disabled(app,monkeypatch):
    owner=create_user("resend-owner@kats.test","OWNER")
    import app.account_recovery as recovery
    sent=[]
    monkeypatch.setattr(recovery,"mail_configured",lambda:True)
    monkeypatch.setattr(recovery,"send_link",lambda user,purpose,secret:sent.append(secret))
    admin=auth_client(app,owner)
    created=admin.post("/api/v1/admin/invitations",headers=csrf(admin),json={
        "full_name":"Resend Tenant","email":"resend@kats.test","role":"TENANT"})
    assert created.status_code==201
    user_id=created.json["user"]["id"]
    assert admin.post("/api/v1/admin/invitations/"+user_id+"/resend",
        headers=csrf(admin)).status_code==200
    assert len(sent)==2
    assert app.test_client().post("/api/v1/auth/complete-token",json={
        "token":sent[0],"new_password":"SecurePasswordABC123!"}).status_code==400
    assert app.test_client().post("/api/v1/auth/complete-token",json={
        "token":sent[1],"new_password":"SecurePasswordABC123!"}).status_code==200
    assert admin.post("/api/v1/admin/invitations/"+user_id+"/resend",
        headers=csrf(admin)).status_code==409
