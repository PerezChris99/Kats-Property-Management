"""Invitation-only onboarding and enumeration-safe password recovery.

Bearer tokens are high entropy, stored only as SHA-256 digests and delivered
through a configured TLS SMTP gateway in URL fragments (not HTTP request logs).
"""
from datetime import datetime, timedelta, timezone
import hashlib
import os
import re
import secrets
from urllib.parse import quote
from argon2 import PasswordHasher
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from .api import roles, data, required_string, fail, audit, serialize
from .extensions import db, limiter
from .models import User, RefreshSession
from .account_models import AccountToken
from .mail import app_origin, mail_configured, send_transactional_email, MailNotConfigured

recovery_api=Blueprint("account_recovery",__name__)
password_hasher=PasswordHasher()
VALID_ROLES={"MANAGER","CARETAKER","ACCOUNTANT","TENANT"}

def digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()

def utcnow():
    return datetime.now(timezone.utc)

def expiration(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

def valid_email(email):
    return isinstance(email,str) and len(email)<=254 and re.fullmatch(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",email) is not None

def revoke_existing(user_id,purpose):
    db.session.query(AccountToken).filter_by(user_id=user_id,purpose=purpose,consumed_at=None).update(
        {AccountToken.consumed_at:utcnow()},synchronize_session=False)

def create_token(user_id,purpose,issuer=None):
    secret=secrets.token_urlsafe(48)
    expiry=utcnow()+timedelta(hours=48 if purpose=="INVITE" else 0.5)
    record=AccountToken(user_id=user_id,purpose=purpose,digest=digest(secret),
                        expires_at=expiry,issued_by=issuer)
    db.session.add(record)
    return secret, record

def send_link(user,purpose,secret):
    target="/account/activate" if purpose=="INVITE" else "/reset-password"
    url=app_origin()+target+"#token="+quote(secret,safe="")
    subject=("Kats — set up your account" if purpose=="INVITE" else
             "Kats — password reset")
    hours=48 if purpose=="INVITE" else 0.5
    body=(f"Hello {user.full_name},\n\n"
          +("You have been invited to Kats Property Management.\n" if purpose=="INVITE" else
            "A password reset was requested for your Kats account.\n")
          +f"Open this one-use link within {hours:g} hours:\n{url}\n\n"
          +"If you did not request this, do not open the link. Your existing password remains unchanged.\n"
          +"Do not share this link. Kats staff will never ask you for a password or one-time link.")
    send_transactional_email(user.email,subject,body)

@recovery_api.post("/admin/invitations")
@roles("OWNER","SUPER_ADMIN")
@limiter.limit("20 per hour")
def invite_user(actor):
    if not mail_configured():
        return fail("Transactional email service is not configured",503)
    obj=data()
    role=required_string(obj,"role",30).upper()
    if role not in VALID_ROLES:
        return fail("This account role cannot be invited",403)
    email=required_string(obj,"email",254).lower()
    name=required_string(obj,"full_name",160)
    if not valid_email(email):
        return fail("A valid recipient email is required")
    if db.session.query(User.id).filter_by(email=email).first():
        return fail("An account already uses this email",409)
    # No admin-shared or emailed initial password; activation creates it.
    new=User(full_name=name,email=email,role=role,
             password_hash=password_hasher.hash(secrets.token_urlsafe(48)),
             is_active=False)
    db.session.add(new)
    db.session.flush()
    secret,token=create_token(new.id,"INVITE",actor.id)
    audit(actor,"account.invitation_issued","user",new.id,role=role)
    db.session.commit()
    try:
        send_link(new,"INVITE",secret)
    except MailNotConfigured:
        token.consumed_at=utcnow()
        db.session.commit()
        return fail("Invitation delivery failed; account remains inactive. Configure email and resend.",503)
    return jsonify(user=serialize(new,"id","email","full_name","role","is_active"),
                   message="Secure invitation sent"),201

@recovery_api.post("/admin/invitations/<user_id>/resend")
@roles("OWNER","SUPER_ADMIN")
@limiter.limit("20 per hour")
def resend_invite(actor,user_id):
    if not mail_configured():
        return fail("Transactional email service is not configured",503)
    user=db.session.get(User,user_id)
    if not user or user.role not in VALID_ROLES or user.is_active:
        return fail("Only pending, inactive invitation accounts can receive a new link",409)
    revoke_existing(user.id,"INVITE")
    secret,token=create_token(user.id,"INVITE",actor.id)
    audit(actor,"account.invitation_resent","user",user.id)
    db.session.commit()
    try:
        send_link(user,"INVITE",secret)
    except MailNotConfigured:
        token.consumed_at=utcnow()
        db.session.commit()
        return fail("Email delivery failed; invitation remains inactive",503)
    return jsonify(message="New invitation sent"),200

@recovery_api.post("/auth/recover")
@limiter.limit("3 per hour")
def request_password_reset():
    obj=data()
    email=obj.get("email","")
    if not isinstance(email,str) or len(email)>254:
        return fail("Valid email required")
    # Same response for unknown, blocked, and unconfigured accounts.
    neutral=(jsonify(message="If an active account matches, recovery instructions will be sent"),202)
    if not valid_email(email) or not mail_configured():
        return neutral
    user=db.session.query(User).filter_by(email=email.lower(),is_active=True).first()
    if not user or user.role=="SERVICE":
        return neutral
    revoke_existing(user.id,"RESET")
    secret,token=create_token(user.id,"RESET")
    db.session.commit()
    try:
        send_link(user,"RESET",secret)
    except MailNotConfigured:
        token.consumed_at=utcnow()
        db.session.commit()
    return neutral

@recovery_api.post("/auth/complete-token")
@limiter.limit("8 per hour")
def complete_token():
    obj=data()
    value=required_string(obj,"token",256)
    password=required_string(obj,"new_password",256)
    if len(password)<12 or len(password)>128:
        return fail("A password of 12–128 characters is required")
    if not re.fullmatch(r"[A-Za-z0-9_\-]{30,256}",value):
        return fail("Invalid or expired account link",400)
    token=db.session.query(AccountToken).filter_by(digest=digest(value)).with_for_update().first()
    if token is None or token.consumed_at is not None or expiration(token.expires_at)<=utcnow():
        return fail("Invalid, expired or already used account link",400)
    user=db.session.query(User).filter_by(id=token.user_id).with_for_update().first()
    if not user or user.role=="SERVICE":
        return fail("Account is not eligible",403)
    if token.purpose=="INVITE" and user.is_active:
        return fail("This invitation has already been activated",409)
    if token.purpose=="RESET" and not user.is_active:
        return fail("Account is disabled",403)
    # One-use token under a database row lock prevents concurrent redemption.
    user.password_hash=password_hasher.hash(password)
    user.is_active=True
    user.session_version+=1
    revoke_existing(user.id,"INVITE")
    revoke_existing(user.id,"RESET")
    db.session.query(RefreshSession).filter_by(user_id=user.id,revoked_at=None).update(
        {RefreshSession.revoked_at:utcnow()},synchronize_session=False)
    audit(user,"account.token_consumed","user",user.id,purpose=token.purpose)
    db.session.commit()
    return jsonify(message="Password updated. Sign in with your new credentials."),200
