import time
from pathlib import Path
from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.entities import Export, Job, JobStatus, Project
from app.repositories.repositories import ArticleRepository, ProjectRepository
from app.services.ai import provider, validate_evidence
from app.services.media import make_captions, render_video, tts_provider
from app.services.video_generation import generate_scene_clips
from app.services.storage import storage_provider

class ScriptState(TypedDict,total=False):
    db:Session; article_id:str; language:str; article_text:str; title:str; article_version_id:str; result:dict; project_id:str; started:float

def load_article(s:ScriptState):
    article=ArticleRepository(s["db"]).get(s["article_id"])
    if not article: raise ValueError("Article not found")
    version=ArticleRepository(s["db"]).latest_version(article.id)
    if not version: raise ValueError("Article has no extracted version")
    return {"article_text":version.text,"title":article.title,"article_version_id":version.id,"started":time.monotonic()}
def generate(s:ScriptState): return {"result":provider().generate(s["article_text"],s["title"],s["language"])}
def ground(s:ScriptState): return {"result":validate_evidence(s["result"],s["article_text"])}
def persist(s:ScriptState):
    r=s["result"]; project=Project(article_id=s["article_id"],article_version_id=s["article_version_id"],title=s["title"],language=s["language"],script=r.get("script",""),scenes=r.get("scenes",[]),evidence=r.get("evidence",[]),unsupported_claims=r.get("unsupported_claims",[]),voice_settings={"provider":get_settings().tts_provider,"language":s["language"]})
    repo=ProjectRepository(s["db"]); repo.save(project); repo.revision(project); return {"project_id":project.id}

script_graph=StateGraph(ScriptState); script_graph.add_node("load_article",load_article); script_graph.add_node("generate",generate); script_graph.add_node("ground",ground); script_graph.add_node("persist",persist)
script_graph.add_edge(START,"load_article"); script_graph.add_edge("load_article","generate"); script_graph.add_edge("generate","ground"); script_graph.add_edge("ground","persist"); script_graph.add_edge("persist",END)
script_workflow=script_graph.compile()

class RenderState(TypedDict,total=False):
    db:Session; project_id:str; job_id:str; project:dict[str,Any]; folder:Path; audio:Path; captions:Path; clips:list[Path]; video:Path; duration:float; started:float

def _stage(s:RenderState,name:str,progress:int,metrics:dict|None=None):
    job=s["db"].get(Job,s["job_id"]); job.status=JobStatus.running; job.stage=name; job.progress=progress
    if metrics: job.metrics={**job.metrics,**metrics}
    s["db"].commit()
def prepare(s:RenderState):
    repo=ProjectRepository(s["db"]); p=repo.get(s["project_id"]); job=s["db"].get(Job,s["job_id"])
    if not p or not job or job.project_id!=p.id: raise ValueError("Render job or project was not found")
    target_version=int(job.metrics.get("project_version",p.version))
    revision=repo.revision_at(p.id,target_version)
    if target_version==p.version and not p.approved: raise ValueError("Project must be approved before rendering")
    if target_version!=p.version and not revision: raise ValueError("The approved project revision is unavailable")
    snapshot=revision.snapshot if revision else {
        "title":p.title,"language":p.language,"script":p.script,"scenes":p.scenes,"evidence":p.evidence,
        "voice_settings":p.voice_settings,"brand_settings":p.brand_settings,"unsupported_claims":p.unsupported_claims,
    }
    project={**snapshot,"id":p.id,"version":target_version,"owner_id":p.owner_id}
    folder=get_settings().storage_root/p.id/f"v{target_version}"; folder.mkdir(parents=True,exist_ok=True); _stage(s,"narration",15)
    return {"project":project,"folder":folder,"started":time.monotonic()}
def narrate(s:RenderState):
    voice={**s["project"].get("voice_settings",{}),"language":s["project"]["language"]}; path=s["folder"]/("narration.wav" if voice.get("provider")=="mock" else "narration.flac")
    job=s["db"].get(Job,s["job_id"]); duration=job.metrics.get("duration_seconds") if path.exists() else None
    if not duration: duration=tts_provider(voice.get("provider")).synthesize(s["project"]["script"],voice,path)
    _stage(s,"captions",45,{"duration_seconds":duration,"narration_complete":True}); return {"audio":path,"duration":duration}
def captions(s:RenderState):
    path=s["folder"]/"captions.json"
    if not path.exists(): make_captions(s["project"]["script"],s["duration"],path)
    _stage(s,"visuals",55,{"captions_complete":True}); return {"captions":path}
def visuals(s:RenderState):
    project={"title":s["project"]["title"],"scenes":s["project"].get("scenes",[])}
    clips=generate_scene_clips(project,s["folder"])
    _stage(s,"compose",80,{"scene_clips_complete":len(clips)}); return {"clips":clips}
def render(s:RenderState):
    path=s["folder"]/"video.mp4"; p=s["project"]
    if not path.exists(): render_video({"title":p["title"],"scenes":p.get("scenes",[]),"brand":p.get("brand_settings",{}),"sourceCredits":p.get("evidence",[])},s["audio"],s["captions"],s["clips"],path,s["duration"])
    _stage(s,"upload",90,{"render_complete":True}); return {"video":path}
def finalize(s:RenderState):
    p=s["project"]; key=f"{p['id']}/v{p['version']}/video.mp4"; location=storage_provider().put(s["video"],key)
    export=s["db"].scalar(select(Export).where(Export.project_id==p["id"],Export.project_version==p["version"]))
    if export:
        export.video_path=location; export.audio_path=str(s["audio"]); export.captions_path=str(s["captions"]); export.duration_seconds=round(s["duration"])
    else:
        export=Export(project_id=p["id"],project_version=p["version"],video_path=location,audio_path=str(s["audio"]),captions_path=str(s["captions"]),duration_seconds=round(s["duration"]),owner_id=p["owner_id"]); s["db"].add(export)
    s["db"].expire_all(); current=ProjectRepository(s["db"]).get(p["id"])
    if current and current.version==p["version"]: current.outputs_valid=True
    job=s["db"].get(Job,s["job_id"]); job.status=JobStatus.completed; job.stage="completed"; job.progress=100; job.metrics={**job.metrics,"rendered_project_version":p["version"],"elapsed_seconds":round(time.monotonic()-s["started"],2)}; s["db"].commit(); return {}

render_graph=StateGraph(RenderState)
for name,fn in (("prepare",prepare),("narrate",narrate),("captions",captions),("visuals",visuals),("render",render),("finalize",finalize)): render_graph.add_node(name,fn)
render_graph.add_edge(START,"prepare"); render_graph.add_edge("prepare","narrate"); render_graph.add_edge("narrate","captions"); render_graph.add_edge("captions","visuals"); render_graph.add_edge("visuals","render"); render_graph.add_edge("render","finalize"); render_graph.add_edge("finalize",END)
render_workflow=render_graph.compile()
