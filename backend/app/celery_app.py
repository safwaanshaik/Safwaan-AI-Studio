from celery import Celery
import os

# Redis URL for Railway
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery(
    "cinematrix",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.app.workers"]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "backend.app.workers.generate_video": {"queue": "gen"},
        "backend.app.workers.post_to_social": {"queue": "social"},
        "backend.app.workers.track_revenue": {"queue": "revenue"},
        "backend.app.workers.discover_trends": {"queue": "trends"},
        "backend.app.workers.auto_generate_from_trends": {"queue": "auto_gen"}
    },

    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,

    # Result backend
    result_expires=3600,

    # Beat schedule for periodic tasks
    beat_schedule={
        "discover-trends": {
            "task": "backend.app.workers.discover_trends",
            "schedule": 21600.0,  # Every 6 hours
        },
        "auto-generate-videos": {
            "task": "backend.app.workers.auto_generate_from_trends",
            "schedule": 25200.0,  # Every 7 hours (offset from trend discovery)
        },
        "track-revenue": {
            "task": "backend.app.workers.track_revenue",
            "schedule": 86400.0,  # Daily
        },
    },
)

# Error handling
@celery_app.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None):
    """Handle task failures."""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Task {task_id} failed: {exception}")
    logger.error(f"Task args: {args}")
    logger.error(f"Task kwargs: {kwargs}")

# Success handling
@celery_app.task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle task successes."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Task {sender.request.id} completed successfully")

if __name__ == "__main__":
    celery_app.start()