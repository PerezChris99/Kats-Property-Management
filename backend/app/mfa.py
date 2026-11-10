"""Encrypted TOTP authenticator enrollment and replay-protected login.

Opt-in at the account layer; production administrators must activate MFA in
business acceptance before they can be considered fully security-approved.
"""
import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from urllib.parse import quote
from cryptography.fernet import Fernet, InvalidToken
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, unset_jwt_cookies
from .api import current_user, data, required_string, fail, audit
from .extensions import db, limiter
from .models import RefreshSession
from datetime import datetime, timezone

mfa_api = Blueprint("mfa",__name__)
hasher = PasswordHasher()

class MfaUnavailable(RuntimeError):
    pass

def cipher():
    key=os.getenv("MFA_ENCRYPTION_KEY")
    if not key:
        raise MfaUnavailable("MFA encryption key is unavailable")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise MfaUnavailable("MFA encryption key is invalid") from exc

def encrypt_secret(secret):
    return cipher().encrypt(secret.encode("ascii")).decode("ascii")

def decrypt_secret(ciphertext):
    if not ciphertext:
        raise MfaUnavailable("MFA secret is missing")
    try:
        return cipher().decrypt(ciphertext.encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise MfaUnavailable("MFA decryption unavailable") from exc

def totp_at(secret, step):
    raw=base64.b32decode(secret,casefold=True)
    digest=hmac.new(raw,struct.pack(">Q",step),hashlib.sha1).digest()
    offset=digest[-1]&15
    integer=struct.unpack(">I",digest[offset:offset+4])[0]&0x7fffffff
    return str(integer % 1000000).zfill(6)

def verify_totp_code(secret, code):
    if not isinstance(code,str) or len(code)!=6 or not code.isdecimal():
        return None
    step=int(time.time()//30)
    matches=[candidate for candidate in (step-1,step,step+1)
             if candidate>=0 and hmac.compare_digest(totp_at(secret,candidate),code)]
    return max(matches) if matches else None

def password_valid(user, candidate):
    try:
        return bool(hasher.verify(user.password_hash,candidate))
    except (VerifyMismatchError,VerificationError):
        return False

def reset_sessions(user):
    user.session_version+=1
    db.session.query(RefreshSession).filter_by(user_id=user.id,revoked_at=None).update(
        {RefreshSession.revoked_at:datetime.now(timezone.utc)},synchronize_session=False)

@mfa_api.get("/auth/mfa/status")
@jwt_required()
def status():
    user=current_user()
    return jsonify(mfa_enabled=bool(user.mfa_enabled),
                   recommended_for=user.role in ("OWNER","SUPER_ADMIN","MANAGER","ACCOUNTANT"))

@mfa_api.post("/auth/mfa/enroll")
@jwt_required()
@limiter.limit("5 per hour")
def enroll():
    user=current_user()
    if user.mfa_enabled:
        return fail("MFA already enabled. Disable with password and authenticator code first",409)
    obj=data()
    password=required_string(obj,"current_password",256)
    if not password_valid(user,password):
        return fail("Current password verification failed",403)
    secret=base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
    try:
        encrypted=encrypt_secret(secret)
    except MfaUnavailable:
        return fail("Authenticator enrollment is not configured",503)
    user.mfa_secret_encrypted=encrypted
    db.session.add(user)
    audit(user,"auth.mfa_enroll_started","user",user.id)
    db.session.commit()
    issuer="Kats Properties"
    uri=f"otpauth://totp/{quote(issuer)}:{quote(user.email)}?secret={secret}&issuer={quote(issuer)}&digits=6&period=30"
    return jsonify(secret=secret,otpauth_uri=uri,
                   notice="Store the code in your authenticator application. Never share the secret; confirm enrollment before signing out")

@mfa_api.post("/auth/mfa/confirm")
@jwt_required()
@limiter.limit("10 per hour")
def confirm():
    user=current_user()
    if user.mfa_enabled or not user.mfa_secret_encrypted:
        return fail("MFA enrollment not pending",409)
    code=required_string(data(),"mfa_code",6)
    try:
        valid=verify_totp_code(decrypt_secret(user.mfa_secret_encrypted),code)
    except MfaUnavailable:
        return fail("Authenticator verification unavailable",503)
    if valid is None:
        return fail("Invalid authenticator code",403)
    user.mfa_enabled=True
    user.mfa_last_step=None
    reset_sessions(user)
    audit(user,"auth.mfa_enabled","user",user.id)
    db.session.commit()
    response=jsonify(message="MFA enabled. Sign in again with password and authenticator code")
    unset_jwt_cookies(response)
    return response

@mfa_api.post("/auth/mfa/disable")
@jwt_required()
@limiter.limit("5 per hour")
def disable():
    user=current_user()
    if not user.mfa_enabled:
        return fail("MFA not enabled",409)
    obj=data()
    password=required_string(obj,"current_password",256)
    code=required_string(obj,"mfa_code",6)
    if not password_valid(user,password):
        return fail("Current password verification failed",403)
    try:
        matched=verify_totp_code(decrypt_secret(user.mfa_secret_encrypted),code)
    except MfaUnavailable:
        return fail("Authenticator verification unavailable",503)
    if matched is None or (user.mfa_last_step is not None and matched<=user.mfa_last_step):
        return fail("Invalid or previously used authenticator code",403)
    user.mfa_enabled=False
    user.mfa_secret_encrypted=None
    user.mfa_last_step=None
    reset_sessions(user)
    audit(user,"auth.mfa_disabled","user",user.id)
    db.session.commit()
    response=jsonify(message="MFA disabled. All sessions signed out")
    unset_jwt_cookies(response)
    return response
