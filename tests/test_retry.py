from app.models.entities import Job, JobStatus
from app.routers.jobs import retry

def test_failed_job_can_be_retried_without_losing_completed_stage_data(db,monkeypatch):
    job=Job(kind="generation",status=JobStatus.failed,stage="failed",attempts=1,max_attempts=3,dedupe_key="x",error="temporary",metrics={"article_id":"a","language":"en"}); db.add(job); db.commit()
    called=[]; monkeypatch.setattr("app.routers.jobs.generate_project.apply_async",lambda **kwargs:called.append(kwargs))
    result=retry(job.id,db)
    assert result.status==JobStatus.queued and result.error is None and called
