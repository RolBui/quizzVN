from celery import Celery

from ai_agent.config import settings


celery_app = Celery(
    "quizzvn_ai_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["ai_agent.tasks"],
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_always_eager=settings.CELERY_EAGER,
    task_eager_propagates=True,
)
