from datetime import datetime
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator
from app.models.entities import JobStatus

class ORMModel(BaseModel): model_config=ConfigDict(from_attributes=True)
class SourceCreate(BaseModel):
    name: str=Field(min_length=1,max_length=160); url: AnyHttpUrl; topics:list[str]=Field(default_factory=list,max_length=20); interval_minutes:int=Field(15,ge=5,le=1440); render_javascript:bool=False
    @field_validator("topics")
    @classmethod
    def normalize(cls,v): return sorted({x.strip().lower() for x in v if x.strip()})
class SourceRead(ORMModel):
    id:str; name:str; url:str; topics:list[str]; interval_minutes:int; enabled:bool; last_collected_at:datetime|None; render_javascript:bool
class SourceUpdate(BaseModel):
    name:str|None=Field(default=None,min_length=1,max_length=160); topics:list[str]|None=None; interval_minutes:int|None=Field(default=None,ge=5,le=1440); enabled:bool|None=None; render_javascript:bool|None=None
class ArticleRead(ORMModel):
    id:str; source_id:str; canonical_url:str; title:str; published_at:datetime|None; current_hash:str; extraction_complete:bool
class ArticleDetail(ArticleRead): text:str; metadata:dict
class ProjectCreate(BaseModel): article_id:str; language:str=Field("en",pattern="^(en|hi)$")
class ProjectUpdate(BaseModel):
    title:str|None=None; script:str|None=None; scenes:list[dict]|None=None; voice_settings:dict|None=None; brand_settings:dict|None=None; unsupported_claims:list[dict]|None=None
class ProjectRead(ORMModel):
    id:str; article_id:str; article_version_id:str; title:str; language:str; script:str; scenes:list; evidence:list; voice_settings:dict; brand_settings:dict
    version:int; approved:bool; outputs_valid:bool; unsupported_claims:list
class JobRead(ORMModel):
    id:str; project_id:str|None; source_id:str|None; kind:str; status:JobStatus; stage:str; progress:int; attempts:int; max_attempts:int; error:str|None; metrics:dict
class ExportRead(ORMModel):
    id:str; project_id:str; project_version:int; video_path:str; audio_path:str|None; captions_path:str|None; duration_seconds:int|None; created_at:datetime
