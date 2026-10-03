import time
from sqlalchemy import select
from app.core.config import get_settings
from app.models.entities import Article, ArticleVersion, Export, Job, Project, ProjectRevision, Source
from app.repositories.repositories import ProjectRepository
from app.routers.projects import approve, edit_project
from app.schemas.api import ProjectUpdate
from app.workflows.story import finalize, prepare

def make_project(db):
    source=Source(name="S",url="https://example.com"); db.add(source); db.flush()
    article=Article(source_id=source.id,canonical_url="https://example.com/a",title="A",current_hash="x"); db.add(article); db.flush()
    version=ArticleVersion(article_id=article.id,content_hash="x",text="text"); db.add(version); db.flush()
    project=Project(article_id=article.id,article_version_id=version.id,title="A",script="old",approved=True,outputs_valid=True); db.add(project); db.commit(); return project

def test_edit_invalidates_approval_and_outputs(db):
    project=make_project(db); result=edit_project(project.id,ProjectUpdate(script="new script"),db)
    assert result.version==2 and not result.approved and not result.outputs_valid
    assert db.query(ProjectRevision).filter_by(project_id=project.id,version=2).count()==1

def test_unsupported_claims_block_approval(db):
    from fastapi import HTTPException
    project=make_project(db); project.unsupported_claims=[{"reason":"missing"}]; db.commit()
    try: approve(project.id,db)
    except HTTPException as exc: assert exc.status_code==409
    else: raise AssertionError("approval should fail")

def test_render_stays_on_approved_revision_when_project_is_edited(db,tmp_path,monkeypatch):
    project=make_project(db); ProjectRepository(db).revision(project)
    job=Job(project_id=project.id,kind="render",dedupe_key="render-v1",metrics={"project_version":1}); db.add(job); db.commit()
    edit_project(project.id,ProjectUpdate(script="version two"),db)
    monkeypatch.setattr(get_settings(),"storage_root",tmp_path)

    state={"db":db,"project_id":project.id,"job_id":job.id}
    prepared=prepare(state); state.update(prepared)
    assert state["project"]["version"]==1
    assert state["project"]["script"]=="old"

    for name in ("narration.flac","captions.json","video.mp4"):
        (state["folder"]/name).write_bytes(b"fixture")
    class FixtureStorage:
        def put(self,local,key): return str(local)
    monkeypatch.setattr("app.workflows.story.storage_provider",lambda:FixtureStorage())
    state.update({"audio":state["folder"]/"narration.flac","captions":state["folder"]/"captions.json","video":state["folder"]/"video.mp4","duration":3.0,"started":time.monotonic()})
    finalize(state)

    db.expire_all(); current=db.get(Project,project.id); export=db.scalar(select(Export))
    assert current.version==2 and not current.outputs_valid
    assert export.project_version==1
