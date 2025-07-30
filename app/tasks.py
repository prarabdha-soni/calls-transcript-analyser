import logging
from datetime import datetime

from celery import Celery
from app.config import settings


celery_app = Celery(
    "sales_analytics",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.task
def process_analytics() -> dict:
    """Process analytics in background"""
    return {"status": "completed", "message": "Analytics processed"}


@celery_app.task
def cleanup_old_data() -> dict:
    """Clean up old data"""
    return {"status": "completed", "message": "Old data cleaned up"}
