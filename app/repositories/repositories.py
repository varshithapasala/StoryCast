from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.models.entities import Article, ArticleVersion, Export, Job, JobStatus, Project, ProjectRevision, Source

class SourceRepository:
    def __init__(self, db:Session, owner="local-user"): self.db=db; self.owner=owner
    def list(self): return list(self.db.scalars(select(Source).where(Source.owner_id==self.owner).order_by(Source.created_at.desc())))
    def get(self,id): return self.db.scalar(select(Source).where(Source.id==id,Source.owner_id==self.owner))
    def create(self,**data):
        obj=Source(owner_id=self.owner,**data); self.db.add(obj); self.db.commit(); self.db.refresh(obj); return obj

class ArticleRepository:
    def __init__(self,db:Session,owner="local-user"): self.db=db; self.owner=owner
    def list(self,topic=None):
        q=select(Article).where(Article.owner_id==self.owner).order_by(desc(Article.published_at),desc(Article.created_at))
        rows=list(self.db.scalars(q))
        return [x for x in rows if not topic or topic.lower() in x.title.lower()]
    def get(self,id): return self.db.scalar(select(Article).where(Article.id==id,Article.owner_id==self.owner))
    def latest_version(self,article_id): return self.db.scalar(select(ArticleVersion).where(ArticleVersion.article_id==article_id).order_by(desc(ArticleVersion.created_at)))
    def by_url(self,url): return self.db.scalar(select(Article).where(Article.canonical_url==url,Article.owner_id==self.owner))

class ProjectRepository:
    def __init__(self,db:Session,owner="local-user"): self.db=db; self.owner=owner
    def list(self): return list(self.db.scalars(select(Project).where(Project.owner_id==self.owner).order_by(desc(Project.updated_at))))
    def get(self,id): return self.db.scalar(select(Project).where(Project.id==id,Project.owner_id==self.owner))
    def save(self,obj): self.db.add(obj); self.db.commit(); self.db.refresh(obj); return obj
    def revision(self,obj):
        snapshot={"title":obj.title,"language":obj.language,"script":obj.script,"scenes":obj.scenes,"evidence":obj.evidence,"voice_settings":obj.voice_settings,"brand_settings":obj.brand_settings,"unsupported_claims":obj.unsupported_claims}
        rev=ProjectRevision(project_id=obj.id,version=obj.version,snapshot=snapshot,owner_id=self.owner); self.db.add(rev); self.db.commit(); return rev
    def revisions(self,id): return list(self.db.scalars(select(ProjectRevision).where(ProjectRevision.project_id==id,ProjectRevision.owner_id==self.owner).order_by(desc(ProjectRevision.version))))
    def revision_at(self,id,version): return self.db.scalar(select(ProjectRevision).where(ProjectRevision.project_id==id,ProjectRevision.version==version,ProjectRevision.owner_id==self.owner))

class JobRepository:
    def __init__(self,db:Session,owner="local-user"): self.db=db; self.owner=owner
    def list(self): return list(self.db.scalars(select(Job).where(Job.owner_id==self.owner).order_by(desc(Job.created_at))))
    def get(self,id): return self.db.scalar(select(Job).where(Job.id==id,Job.owner_id==self.owner))
    def create_unique(self,*,kind,dedupe_key,project_id=None,source_id=None):
        found=self.db.scalar(select(Job).where(Job.dedupe_key==dedupe_key))
        if found and found.status in (JobStatus.queued,JobStatus.running,JobStatus.completed): return found,False
        if found and found.attempts>=found.max_attempts: return found,False
        if found:
            found.status=JobStatus.queued; found.stage="queued"; found.progress=0; found.error=None
            self.db.commit(); return found,True
        job=Job(kind=kind,dedupe_key=dedupe_key,project_id=project_id,source_id=source_id,owner_id=self.owner)
        self.db.add(job); self.db.commit(); self.db.refresh(job); return job,True

class ExportRepository:
    def __init__(self,db:Session,owner="local-user"): self.db=db; self.owner=owner
    def list(self): return list(self.db.scalars(select(Export).where(Export.owner_id==self.owner).order_by(desc(Export.created_at))))
    def get(self,id): return self.db.scalar(select(Export).where(Export.id==id,Export.owner_id==self.owner))
