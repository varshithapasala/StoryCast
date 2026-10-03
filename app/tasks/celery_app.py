from celery import Celery
from app.core.config import get_settings

s=get_settings()
celery_app=Celery("storycast",broker=s.celery_broker_url,backend=s.celery_result_backend,include=["app.tasks.jobs"])
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=840,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={"collect-due-sources":{"task":"app.tasks.jobs.collect_due_sources","schedule":60.0,"options":{"queue":"collection"}}},
    task_routes={
        "app.tasks.jobs.collect*":{"queue":"collection"},
        "app.tasks.jobs.generate*":{"queue":"generation"},
        "app.tasks.jobs.render*":{"queue":"rendering"},
    },
)

