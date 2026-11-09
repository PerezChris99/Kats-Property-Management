"""One-time activation/reset credentials. Never persist the bearer secret itself."""
from .extensions import db
from .models import new_id, utcnow

class AccountToken(db.Model):
    __tablename__="account_tokens"
    id=db.Column(db.String(36),primary_key=True,default=new_id)
    user_id=db.Column(db.String(36),db.ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True)
    purpose=db.Column(db.String(16),nullable=False)
    digest=db.Column(db.String(64),nullable=False,unique=True)
    expires_at=db.Column(db.DateTime(timezone=True),nullable=False,index=True)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=utcnow)
    consumed_at=db.Column(db.DateTime(timezone=True),nullable=True)
    issued_by=db.Column(db.String(36),db.ForeignKey("users.id",ondelete="SET NULL"),nullable=True)
    __table_args__=(
        db.CheckConstraint("purpose IN ('INVITE','RESET')",name="ck_account_token_purpose"),
    )
