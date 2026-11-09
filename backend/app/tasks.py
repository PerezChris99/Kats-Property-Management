import os
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "kats",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=120,
    timezone="Africa/Kampala",
    enable_utc=True,
    beat_schedule={
        "create-rent-invoices-monthly": {
            "task": "app.tasks.generate_rent_invoices",
            "schedule": crontab(minute=10, hour=1, day_of_month=1),
        },
        "rent-reminders-daily": {
            "task": "app.tasks.generate_rent_reminders",
            "schedule": crontab(minute=0, hour=9),
        },
        "lease-expiry-daily": {
            "task": "app.tasks.generate_lease_expiries",
            "schedule": crontab(minute=10, hour=9),
        },
        "fiscal-outbox-poll": {
            "task": "app.tasks.poll_fiscal_submissions",
            "schedule": crontab(minute="*/15"),
        },
        "mobile-money-reconciliation": {
            "task": "app.tasks.poll_mobile_transactions",
            "schedule": crontab(minute="*/5"),
        },
        "prune-temporary-credentials-daily": {
            "task": "app.tasks.prune_ephemeral_tokens",
            "schedule": crontab(minute=40, hour=3),
        },
    },
)

@celery_app.task(name="app.tasks.generate_rent_invoices", autoretry_for=(Exception,),
                 retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3})
def generate_rent_invoices():
    """The scheduler issues only whole-month invoices; partial periods require review."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app import create_app
    from app.billing import generate_monthly_rent
    application = create_app()
    with application.app_context():
        return generate_monthly_rent(datetime.now(ZoneInfo("Africa/Kampala")).date())

# No payment or fiscal task is enabled without a verified provider.


@celery_app.task(name="app.tasks.generate_rent_reminders",
                 autoretry_for=(Exception,), retry_backoff=True,
                 retry_kwargs={"max_retries": 3})
def generate_rent_reminders():
    from app import create_app
    from app.notifications import rent_reminder_run
    with create_app().app_context():
        return rent_reminder_run()

@celery_app.task(name="app.tasks.generate_lease_expiries",
                 autoretry_for=(Exception,), retry_backoff=True,
                 retry_kwargs={"max_retries": 3})
def generate_lease_expiries():
    from app import create_app
    from app.notifications import expiring_lease_run
    with create_app().app_context():
        return expiring_lease_run()


@celery_app.task(name="app.tasks.poll_fiscal_submissions",
                 autoretry_for=(Exception,), retry_backoff=True,
                 retry_kwargs={"max_retries": 3})
def poll_fiscal_submissions():
    from app import create_app
    from app.efris_gateway import run_fiscal_batch
    with create_app().app_context():
        return run_fiscal_batch()

@celery_app.task(name="app.tasks.poll_mobile_transactions",
                 autoretry_for=(Exception,), retry_backoff=True,
                 retry_kwargs={"max_retries": 3})
def poll_mobile_transactions():
    from app import create_app
    from app.extra_models import ProviderAttempt
    from app.settlement import verify_and_post
    from app.providers import ProviderError
    from app.extensions import db
    with create_app().app_context():
        pending=db.session.query(ProviderAttempt).filter(
            ProviderAttempt.status.in_(["INITIATED","PENDING","RETRYING","UNVERIFIED"])
        ).order_by(ProviderAttempt.created_at).limit(30).all()
        attempted=0
        for attempt in pending:
            if os.getenv(attempt.provider+"_ENABLED","false").lower()!="true":
                continue
            if attempt.verification_attempts>=40:
                attempt.status="MANUAL_REVIEW"
                attempt.last_error_code="POLL_LIMIT_EXCEEDED"
                db.session.commit()
                continue
            verify_and_post(attempt.payment_id)
            attempted+=1
        return {"checked":attempted}


@celery_app.task(name="app.tasks.prune_ephemeral_tokens",
                 autoretry_for=(Exception,), retry_backoff=True,
                 retry_kwargs={"max_retries": 2})
def prune_ephemeral_tokens():
    from app import create_app
    from app.retention import prune_ephemeral_credentials
    with create_app().app_context():
        return prune_ephemeral_credentials()
