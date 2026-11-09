import os
from celery import Celery

celery_app = Celery(
    "kats",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_time_limit=120)
# No simulated payment or EFRIS task is allowed to post live financial events.
