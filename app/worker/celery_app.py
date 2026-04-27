from celery import Celery


from ..config import settings

celery = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    result_expires=3600,  # Results expire in 1 hour
)

celery.conf.task_routes = {
    "app.worker.tasks.*": {"queue": "downloads"},
}
