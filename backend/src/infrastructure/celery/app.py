from __future__ import annotations

from celery import Celery
from celery.signals import worker_init

from src.infrastructure.config import get_settings

settings = get_settings()

celery_app = Celery(
    "instagram_reel_processor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@worker_init.connect
def init_worker(**kwargs):
    """Wire port implementations when Celery worker starts."""
    from src.container import init_container

    init_container()
