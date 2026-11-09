from datetime import timedelta
from app.extensions import db
from app.models import RefreshSession, utcnow
from app.account_models import AccountToken
from app.retention import prune_ephemeral_credentials
from conftest import create_user

def test_expired_temporary_credentials_pruned_without_affecting_live_tokens(app):
    owner=create_user("retention@kats.test","OWNER")
    old=utcnow()-timedelta(days=45)
    future=utcnow()+timedelta(hours=2)
    expired=RefreshSession(user_id=owner.id,token_jti="expired-session-01",expires_at=old)
    live=RefreshSession(user_id=owner.id,token_jti="valid-session-01",expires_at=future)
    long_expired=AccountToken(user_id=owner.id,purpose="RESET",digest="a"*64,expires_at=old)
    active=AccountToken(user_id=owner.id,purpose="RESET",digest="b"*64,expires_at=future)
    db.session.add_all([expired,live,long_expired,active]);db.session.commit()
    expired_id,live_id,old_token_id,active_id=expired.id,live.id,long_expired.id,active.id
    counts=prune_ephemeral_credentials()
    db.session.expunge_all()
    assert counts=={"refresh_sessions":1,"account_tokens":1}
    assert db.session.get(RefreshSession,live_id) is not None
    assert db.session.get(AccountToken,active_id) is not None
    assert db.session.get(RefreshSession,expired_id) is None
    assert db.session.get(AccountToken,old_token_id) is None
    assert prune_ephemeral_credentials()=={"refresh_sessions":0,"account_tokens":0}

def test_pruning_rejects_unbounded_ranges(app):
    for n in (0,-1,6,366):
        try:
            prune_ephemeral_credentials(retention_days=n)
        except ValueError:
            pass
        else:
            assert False
    try:
        prune_ephemeral_credentials(batch_size=10000)
    except ValueError:
        pass
    else:
        assert False
