from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.repositories import JobRepository, ProjectRepository
from app.schemas.api import JobRead, ProjectRead, ProjectUpdate
from app.tasks.jobs import render_project

router=APIRouter(prefix="/projects",tags=["projects"])
@router.get("",response_model=list[ProjectRead])
def list_projects(db:Session=Depends(get_db)): return ProjectRepository(db).list()
@router.get("/{project_id}",response_model=ProjectRead)
def get_project(project_id:str,db:Session=Depends(get_db)):
    obj=ProjectRepository(db).get(project_id)
    if not obj: raise HTTPException(404,"Project not found")
    return obj
@router.patch("/{project_id}",response_model=ProjectRead)
def edit_project(project_id:str,data:ProjectUpdate,db:Session=Depends(get_db)):
    repo=ProjectRepository(db); obj=repo.get(project_id)
    if not obj: raise HTTPException(404,"Project not found")
    values=data.model_dump(exclude_unset=True)
    for key,value in values.items(): setattr(obj,key,value)
    obj.version+=1; obj.approved=False; obj.approved_at=None; obj.outputs_valid=False
    repo.save(obj); repo.revision(obj); return obj
@router.get("/{project_id}/revisions")
def revisions(project_id:str,db:Session=Depends(get_db)):
    repo=ProjectRepository(db)
    if not repo.get(project_id): raise HTTPException(404,"Project not found")
    return [{"id":r.id,"version":r.version,"snapshot":r.snapshot,"created_at":r.created_at} for r in repo.revisions(project_id)]
@router.post("/{project_id}/approve",response_model=ProjectRead)
def approve(project_id:str,db:Session=Depends(get_db)):
    repo=ProjectRepository(db); obj=repo.get(project_id)
    if not obj: raise HTTPException(404,"Project not found")
    if obj.unsupported_claims: raise HTTPException(409,"Resolve unsupported claims before approval")
    obj.approved=True; obj.approved_at=datetime.now(timezone.utc); return repo.save(obj)
@router.post("/{project_id}/render",response_model=JobRead,status_code=202)
def render(project_id:str,db:Session=Depends(get_db)):
    obj=ProjectRepository(db).get(project_id)
    if not obj: raise HTTPException(404,"Project not found")
    if not obj.approved: raise HTTPException(409,"Approve project before rendering")
    job,enqueue=JobRepository(db).create_unique(kind="render",dedupe_key=f"render:{obj.id}:v{obj.version}",project_id=obj.id)
    job.metrics={**job.metrics,"project_version":obj.version}; db.commit()
    if enqueue: render_project.apply_async(args=[job.id,obj.id],queue="rendering")
    return job
