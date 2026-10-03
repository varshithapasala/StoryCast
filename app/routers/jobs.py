from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.repositories import JobRepository
from app.models.entities import JobStatus
from app.schemas.api import JobRead
from app.tasks.jobs import collect_source, generate_project, render_project

router=APIRouter(prefix="/jobs",tags=["jobs"])
@router.get("",response_model=list[JobRead])
def list_jobs(db:Session=Depends(get_db)): return JobRepository(db).list()
@router.post("/{job_id}/retry",response_model=JobRead,status_code=202)
def retry(job_id:str,db:Session=Depends(get_db)):
    job=JobRepository(db).get(job_id)
    if not job: raise HTTPException(404,"Job not found")
    if job.status.value!="failed" or job.attempts>=job.max_attempts: raise HTTPException(409,"Job cannot be retried")
    job.status=JobStatus.queued; job.stage="queued"; job.error=None; db.commit()
    if job.kind=="collection": collect_source.apply_async(args=[job.id,job.source_id],queue="collection")
    elif job.kind=="generation": generate_project.apply_async(args=[job.id,job.metrics["article_id"],job.metrics["language"]],queue="generation")
    else: render_project.apply_async(args=[job.id,job.project_id],queue="rendering")
    return job
