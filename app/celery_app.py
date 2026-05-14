from celery import Celery
from kombu import Exchange, Queue
from app.core.config import settings

celery_app = Celery(
    "careeros",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Berlin",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max per task
    
    # Queue Isolation
    task_queues=(
        Queue('scraping', Exchange('scraping'), routing_key='scraping.#'),
        Queue('scoring', Exchange('scoring'), routing_key='scoring.#'),
        Queue('apply', Exchange('apply'), routing_key='apply.#'),
        Queue('retry', Exchange('retry'), routing_key='retry.#'),
        Queue('dead_letter', Exchange('dead_letter'), routing_key='dead_letter.#'),
        Queue('observability', Exchange('observability'), routing_key='observability.#'),
    ),
    task_default_queue='apply',
    task_default_exchange='apply',
    task_default_routing_key='apply.default',

    # Enable worker state visibility
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Reject on worker lost to allow another worker to pick it up
    task_reject_on_worker_lost=True,
    task_acks_late=True
)

# Autodiscover tasks from agents module
celery_app.autodiscover_tasks(["app.agents"])
