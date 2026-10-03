from datetime import datetime, timedelta, timezone
import time
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.models.entities import Job, JobStatus, Source
from app.repositories.repositories import JobRepository
from app.services.collection import CollectionService
from app.tasks.celery_app import celery_app
from app.workflows.story import render_workflow, script_workflow

def fail(db,job_id,exc):
    job=db.get(Job,job_id)
    if job: job.status=JobStatus.failed; job.stage="failed"; job.error=str(exc)[:4000]; db.commit()

@celery_app.task(bind=True,autoretry_for=(ConnectionError,TimeoutError),retry_backoff=True,retry_kwargs={"max_retries":3})
def collect_source(self,job_id,source_id):
    with SessionLocal() as db:
        try:
            started=time.monotonic()
            job=db.get(Job,job_id); job.status=JobStatus.running; job.stage="discovering"; job.progress=10; job.attempts+=1; db.commit()
            source=db.get(Source,source_id); result=CollectionService(db).collect(source)
            job=db.get(Job,job_id); job.status=JobStatus.completed; job.stage="completed"; job.progress=100; job.metrics={**result,"elapsed_seconds":round(time.monotonic()-started,2)}; db.commit()
        except Exception as exc: fail(db,job_id,exc); raise

@celery_app.task
def collect_due_sources():
    with SessionLocal() as db:
        for source in db.scalars(select(Source).where(Source.enabled.is_(True))):
            last=source.last_collected_at
            if last and last.tzinfo is None: last=last.replace(tzinfo=timezone.utc)
            due=not last or last+timedelta(minutes=source.interval_minutes)<=datetime.now(timezone.utc)
            if due:
                job,enqueue=JobRepository(db).create_unique(kind="collection",dedupe_key=f"scheduled:{source.id}:{source.last_collected_at}",source_id=source.id)
                if enqueue: collect_source.apply_async(args=[job.id,source.id],queue="collection")

@celery_app.task(bind=True,autoretry_for=(ConnectionError,TimeoutError),retry_backoff=True,retry_kwargs={"max_retries":2})
def generate_project(self,job_id,article_id,language):
    with SessionLocal() as db:
        try:
            started=time.monotonic()
            job=db.get(Job,job_id); job.status=JobStatus.running; job.stage="writing"; job.progress=20; job.attempts+=1; db.commit()
            result=script_workflow.invoke({"db":db,"article_id":article_id,"language":language})
            metrics=result["result"].get("_metrics",{}); settings=get_settings(); metrics["estimated_cost_usd"]=round((metrics.get("input_tokens",0)*settings.model_input_cost_per_million+metrics.get("output_tokens",0)*settings.model_output_cost_per_million)/1_000_000,6)
            job=db.get(Job,job_id); job.project_id=result["project_id"]; job.status=JobStatus.completed; job.stage="completed"; job.progress=100; job.metrics={**job.metrics,**metrics,"elapsed_seconds":round(time.monotonic()-started,2)}; db.commit()
        except Exception as exc: fail(db,job_id,exc); raise

@celery_app.task(bind=True,autoretry_for=(ConnectionError,TimeoutError,SoftTimeLimitExceeded),retry_backoff=True,retry_kwargs={"max_retries":2},soft_time_limit=3500,time_limit=3600)
def render_project(self,job_id,project_id):
    with SessionLocal() as db:
        try:
            job=db.get(Job,job_id); job.attempts+=1; db.commit()
            render_workflow.invoke({"db":db,"project_id":project_id,"job_id":job_id})
        except Exception as exc: fail(db,job_id,exc); raise
