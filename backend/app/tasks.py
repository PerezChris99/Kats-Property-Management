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
