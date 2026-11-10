from cryptography.fernet import Fernet
from app.mfa import totp_at, verify_totp_code, decrypt_secret
from app.extensions import db
from conftest import create_user,auth_client,csrf

def test_totp_enrollment_secure_login_and_replay_rejection(app,monkeypatch):
    monkeypatch.setenv("MFA_ENCRYPTION_KEY",Fernet.generate_key().decode())
    monkeypatch.setattr("app.mfa.time.time",lambda:1800000000)
    user=create_user("mfa-user@kats.test","OWNER")
    client=auth_client(app,user)
    enrolled=client.post("/api/v1/auth/mfa/enroll",headers=csrf(client),json={
        "current_password":"ValidPassword123!"})
    assert enrolled.status_code==200,enrolled.json
    ciphertext=db.session.get(type(user),user.id).mfa_secret_encrypted
    assert ciphertext and enrolled.json["secret"] not in ciphertext
    secret=decrypt_secret(ciphertext)
    code=totp_at(secret,1800000000//30)
    confirmed=client.post("/api/v1/auth/mfa/confirm",headers=csrf(client),json={"mfa_code":code})
    assert confirmed.status_code==200,confirmed.json
    bad=app.test_client().post("/api/v1/auth/login",json={
        "email":user.email,"password":"ValidPassword123!"})
    assert bad.status_code==401
    log=app.test_client().post("/api/v1/auth/login",json={
        "email":user.email,"password":"ValidPassword123!","mfa_code":code})
    assert log.status_code==200,log.json
    reuse=app.test_client().post("/api/v1/auth/login",json={
        "email":user.email,"password":"ValidPassword123!","mfa_code":code})
    assert reuse.status_code==401
