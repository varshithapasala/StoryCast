from sqlalchemy import select
from app.core.config import get_settings
from app.models.entities import Article, ArticleVersion, Export, Job, JobStatus, Project, Source
from app.workflows.story import render_workflow, script_workflow

class FixtureScriptProvider:
    def generate(self,article,title,language):
        quote="A verified fact appears here."
        return {"script":f"{quote} "*12,"evidence":[{"id":"e1","quote":quote}],"scenes":[{"id":"s1","narration":quote,"on_screen_text":"Verified fact","visual_prompt":"abstract newsroom","evidence_ids":["e1"],"duration_seconds":3,"transition":"cut"}],"unsupported_claims":[],"_metrics":{"provider":"fixture","input_tokens":10,"output_tokens":5}}

class FixtureTTS:
    def synthesize(self,text,voice,target): target.write_bytes(b"fixture wav"); return 3.0

class FixtureStorage:
    def put(self,local,key): return str(local)

def test_complete_article_to_mp4_state_machine(db,tmp_path,monkeypatch):
    source=Source(name="Source",url="https://example.com"); db.add(source); db.flush()
    text="A verified fact appears here. More context follows for the report."
    article=Article(source_id=source.id,canonical_url="https://example.com/a",title="Verified report",current_hash="hash"); db.add(article); db.flush()
    version=ArticleVersion(article_id=article.id,content_hash="hash",text=text); db.add(version); db.commit()
    monkeypatch.setattr("app.workflows.story.provider",lambda:FixtureScriptProvider())
    scripted=script_workflow.invoke({"db":db,"article_id":article.id,"language":"en"})
    project_id=scripted["project_id"]; project=db.get(Project,project_id); project.approved=True; db.commit()
    job=Job(project_id=project.id,kind="render",dedupe_key="render-fixture"); db.add(job); db.commit()
    monkeypatch.setattr(get_settings(),"storage_root",tmp_path)
    monkeypatch.setattr("app.workflows.story.tts_provider",lambda *_:FixtureTTS())
    monkeypatch.setattr("app.workflows.story.storage_provider",lambda:FixtureStorage())
    clip=tmp_path/"scene.mp4"; clip.write_bytes(b"fixture clip")
    monkeypatch.setattr("app.workflows.story.generate_scene_clips",lambda project,folder:[clip])
    monkeypatch.setattr("app.workflows.story.render_video",lambda project,audio,captions,clips,target,duration:target.write_bytes(b"fixture mp4"))
    render_workflow.invoke({"db":db,"project_id":project.id,"job_id":job.id})
    export=db.scalar(select(Export)); db.refresh(job)
    assert export and export.video_path.endswith("video.mp4")
    assert job.status==JobStatus.completed and job.progress==100
    assert (tmp_path/project.id/"v1"/"video.mp4").read_bytes()==b"fixture mp4"
