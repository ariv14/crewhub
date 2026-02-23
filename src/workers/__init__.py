from celery import Celery

from src.config import settings

celery_app = Celery("a2a_marketplace", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "health-check-all-agents": {
            "task": "src.workers.health_checker.check_all_agents",
            "schedule": settings.health_check_interval_seconds,
        },
        "reputation-decay": {
            "task": "src.workers.reputation_updater.apply_reputation_decay",
            "schedule": 86400,  # Daily
        },
    },
)
