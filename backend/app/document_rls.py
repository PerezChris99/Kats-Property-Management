"""Per-request PostgreSQL row-security context for private documents and tenancy records.

Scope is derived from a *verified* JWT and the database, never from client
headers. SET LOCAL values are reapplied after each commit/new transaction.
No session-scoped SET statements are used, so pooled connections cannot leak
one tenant's row context to another.
"""
from contextvars import ContextVar
from contextlib import contextmanager
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from .extensions import db
from .models import Tenant
from .api import current_user

_SCOPE=ContextVar("kats_document_rls_scope",default=None)
_CONTEXT_SQL=text(
    "SELECT set_config('kats.actor_role', :role, true), "
    "set_config('kats.actor_user_id', :user_id, true), "
    "set_config('kats.actor_tenant_id', :tenant_id, true)"
)

@event.listens_for(Session, "after_begin")
def install_scope_for_new_transaction(session, transaction, connection):
    scope=_SCOPE.get()
    if scope and connection.dialect.name=="postgresql":
        connection.execute(_CONTEXT_SQL,scope)

def begin_document_scope():
    if db.engine.dialect.name!="postgresql":
        return
    verify_jwt_in_request(optional=True)
    if not get_jwt_identity():
        return
    user=current_user()  # Verifies is_active and server-side session version.
    # The tenants table itself is RLS-protected. Establish a provisional
    # authenticated identity before resolving the linked tenant profile, then
    # replace its empty tenant id with the verified database mapping.
    scope={"role":user.role,"user_id":user.id,"tenant_id":""}
    token=_SCOPE.set(scope)
    g.kats_rls_token=token
    db.session.execute(_CONTEXT_SQL,scope)
    if user.role=="TENANT":
        scope["tenant_id"]=db.session.query(Tenant.id).filter_by(
            user_id=user.id).scalar() or ""
        db.session.execute(_CONTEXT_SQL,scope)

def clear_document_scope(_error=None):
    token=getattr(g,"kats_rls_token",None)
    if token is not None:
        _SCOPE.reset(token)
        g.kats_rls_token=None

@contextmanager
def trusted_worker_scope():
    """Only Celery worker execution should call this, never an API endpoint.

    This context is not inferred from request inputs. It survives transaction
    restarts but is cleared after the task, preventing pooled-connection leaks.
    """
    token = _SCOPE.set({"role": "SERVICE", "user_id": "", "tenant_id": ""})
    try:
        yield
    finally:
        _SCOPE.reset(token)
