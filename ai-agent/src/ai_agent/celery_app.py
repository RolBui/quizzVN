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
    task_default_priority=0,
    task_inherit_parent_priority=True,
    broker_transport_options={
        "priority_steps": list(range(10)),
        "sep": ":",
    },
)
if settings.TASK_RATE_LIMIT:
    celery_app.conf.task_annotations = {
        "ai_agent.generate_exam": {"rate_limit": settings.TASK_RATE_LIMIT},
    }
