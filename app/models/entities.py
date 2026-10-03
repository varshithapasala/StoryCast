import enum, uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

def now_utc(): return datetime.now(timezone.utc)

class JobStatus(str, enum.Enum):
    queued="queued"; running="running"; completed="completed"; failed="failed"

class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

class Source(IdMixin, Base):
    __tablename__="sources"
    name: Mapped[str]=mapped_column(String(160)); url: Mapped[str]=mapped_column(String(2048), unique=True)
    topics: Mapped[list]=mapped_column(JSON, default=list); interval_minutes: Mapped[int]=mapped_column(Integer, default=15)
    enabled: Mapped[bool]=mapped_column(Boolean, default=True); last_collected_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    render_javascript: Mapped[bool]=mapped_column(Boolean,default=False)
    owner_id: Mapped[str]=mapped_column(String(64), default="local-user", index=True)

class Article(IdMixin, Base):
    __tablename__="articles"; __table_args__=(UniqueConstraint("canonical_url","owner_id"),)
    source_id: Mapped[str]=mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    canonical_url: Mapped[str]=mapped_column(String(2048)); title: Mapped[str]=mapped_column(String(500))
    published_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True); current_hash: Mapped[str]=mapped_column(String(64), index=True)
    extraction_complete: Mapped[bool]=mapped_column(Boolean, default=True); owner_id: Mapped[str]=mapped_column(String(64), default="local-user", index=True)
    versions: Mapped[list["ArticleVersion"]]=relationship(back_populates="article", cascade="all, delete-orphan")

class ArticleVersion(IdMixin, Base):
    __tablename__="article_versions"; __table_args__=(UniqueConstraint("article_id","content_hash"),)
    article_id: Mapped[str]=mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    content_hash: Mapped[str]=mapped_column(String(64)); text: Mapped[str]=mapped_column(Text); metadata_json: Mapped[dict]=mapped_column(JSON, default=dict)
    article: Mapped[Article]=relationship(back_populates="versions")

class Project(IdMixin, Base):
    __tablename__="projects"
    article_id: Mapped[str]=mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), index=True)
    article_version_id: Mapped[str]=mapped_column(ForeignKey("article_versions.id")); title: Mapped[str]=mapped_column(String(500))
    language: Mapped[str]=mapped_column(String(12), default="en"); script: Mapped[str]=mapped_column(Text, default="")
    scenes: Mapped[list]=mapped_column(JSON, default=list); evidence: Mapped[list]=mapped_column(JSON, default=list)
    voice_settings: Mapped[dict]=mapped_column(JSON, default=dict); brand_settings: Mapped[dict]=mapped_column(JSON, default=dict)
    version: Mapped[int]=mapped_column(Integer, default=1); approved: Mapped[bool]=mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True); outputs_valid: Mapped[bool]=mapped_column(Boolean, default=False)
    unsupported_claims: Mapped[list]=mapped_column(JSON, default=list); owner_id: Mapped[str]=mapped_column(String(64), default="local-user", index=True)

class ProjectRevision(IdMixin, Base):
    __tablename__="project_revisions"; __table_args__=(UniqueConstraint("project_id","version"),)
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id",ondelete="CASCADE"),index=True); version: Mapped[int]=mapped_column(Integer)
    snapshot: Mapped[dict]=mapped_column(JSON); owner_id: Mapped[str]=mapped_column(String(64),default="local-user",index=True)

class Job(IdMixin, Base):
    __tablename__="jobs"
    project_id: Mapped[str|None]=mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    source_id: Mapped[str|None]=mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str]=mapped_column(String(50), index=True); status: Mapped[JobStatus]=mapped_column(Enum(JobStatus), default=JobStatus.queued, index=True)
    stage: Mapped[str]=mapped_column(String(80), default="queued"); progress: Mapped[int]=mapped_column(Integer, default=0)
    attempts: Mapped[int]=mapped_column(Integer, default=0); max_attempts: Mapped[int]=mapped_column(Integer, default=3)
    dedupe_key: Mapped[str]=mapped_column(String(180), unique=True); error: Mapped[str|None]=mapped_column(Text, nullable=True)
    metrics: Mapped[dict]=mapped_column(JSON, default=dict); owner_id: Mapped[str]=mapped_column(String(64), default="local-user", index=True)

class Export(IdMixin, Base):
    __tablename__="exports"
    project_id: Mapped[str]=mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True); project_version: Mapped[int]=mapped_column(Integer)
    video_path: Mapped[str]=mapped_column(String(2048)); audio_path: Mapped[str|None]=mapped_column(String(2048), nullable=True)
    captions_path: Mapped[str|None]=mapped_column(String(2048), nullable=True); duration_seconds: Mapped[int|None]=mapped_column(Integer, nullable=True)
    owner_id: Mapped[str]=mapped_column(String(64), default="local-user", index=True)
