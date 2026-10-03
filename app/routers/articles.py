from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.repositories import ArticleRepository, JobRepository
from app.schemas.api import ArticleDetail, ArticleRead, JobRead, ProjectCreate
from app.tasks.jobs import generate_project

router=APIRouter(prefix="/articles",tags=["articles"])
@router.get("",response_model=list[ArticleRead])
def list_articles(topic:str|None=Query(None),db:Session=Depends(get_db)): return ArticleRepository(db).list(topic)
@router.get("/{article_id}",response_model=ArticleDetail)
def get_article(article_id:str,db:Session=Depends(get_db)):
    repo=ArticleRepository(db); article=repo.get(article_id)
    if not article: raise HTTPException(404,"Article not found")
    version=repo.latest_version(article.id); return ArticleDetail.model_validate(article).model_copy(update={"text":version.text,"metadata":version.metadata_json})
@router.post("/{article_id}/generate",response_model=JobRead,status_code=202)
def generate(article_id:str,data:ProjectCreate,db:Session=Depends(get_db)):
    repo=ArticleRepository(db); article=repo.get(article_id)
    if not article or data.article_id!=article_id: raise HTTPException(404,"Article not found")
    if not article.extraction_complete: raise HTTPException(409,"Article extraction is incomplete")
    version=repo.latest_version(article.id); key=f"script:{version.id}:{data.language}"
    job,enqueue=JobRepository(db).create_unique(kind="generation",dedupe_key=key)
    job.metrics={"article_id":article.id,"language":data.language}; db.commit()
    if enqueue: generate_project.apply_async(args=[job.id,article.id,data.language],queue="generation")
    return job
