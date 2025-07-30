from app.celery_app import celery_app
import logging
from datetime import datetime


@celery_app.task
def recalculate_analytics():
    logging.basicConfig(level=logging.INFO)
    logging.info(
        f"[Celery] Recalculating analytics at {datetime.utcnow().isoformat()}..."
    )
    return {"status": "success", "timestamp": datetime.utcnow().isoformat()}
