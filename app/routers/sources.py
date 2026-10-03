from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.repositories import JobRepository, SourceRepository
from app.schemas.api import JobRead, SourceCreate, SourceRead, SourceUpdate
from app.services.url_safety import UnsafeURLError, validate_public_url
from app.tasks.jobs import collect_source

router=APIRouter(prefix="/sources",tags=["sources"])
@router.get("",response_model=list[SourceRead])
def list_sources(db:Session=Depends(get_db)): return SourceRepository(db).list()
@router.post("",response_model=SourceRead,status_code=201)
def add_source(data:SourceCreate,db:Session=Depends(get_db)):
    try: url=validate_public_url(str(data.url))
    except UnsafeURLError as exc: raise HTTPException(422,str(exc))
    try: return SourceRepository(db).create(name=data.name,url=url,topics=data.topics,interval_minutes=data.interval_minutes,render_javascript=data.render_javascript)
    except IntegrityError: db.rollback(); raise HTTPException(409,"Source URL already exists")
@router.patch("/{source_id}",response_model=SourceRead)
def update_source(source_id:str,data:SourceUpdate,db:Session=Depends(get_db)):
    source=SourceRepository(db).get(source_id)
    if not source: raise HTTPException(404,"Source not found")
    for key,value in data.model_dump(exclude_unset=True).items(): setattr(source,key,value)
    db.commit(); db.refresh(source); return source
@router.post("/{source_id}/collect",response_model=JobRead,status_code=202)
def collect(source_id:str,db:Session=Depends(get_db)):
    source=SourceRepository(db).get(source_id)
    if not source: raise HTTPException(404,"Source not found")
    job,enqueue=JobRepository(db).create_unique(kind="collection",dedupe_key=f"collect:{source.id}:{source.last_collected_at}",source_id=source.id)
    if enqueue: collect_source.apply_async(args=[job.id,source.id],queue="collection")
    return job
