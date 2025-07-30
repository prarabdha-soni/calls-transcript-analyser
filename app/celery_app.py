from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "sales_analytics",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "nightly-analytics-recalculation": {
            "task": "app.tasks.recalculate_analytics",
            "schedule": crontab(hour=2, minute=0),  # Every night at 2am UTC
        },
    },
)
