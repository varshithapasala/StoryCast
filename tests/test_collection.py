from app.models.entities import Source
from app.services.collection import CollectionService

HTML="""<html><head><title>Verified title</title></head><body><article><p>{}</p></article></body></html>""".format("Evidence sentence. "*40)

def test_extraction_and_deduplication_preserves_changed_versions(db,monkeypatch):
    source=Source(name="Example",url="https://news.example",topics=[]); db.add(source); db.commit()
    service=CollectionService(db); monkeypatch.setattr(service,"_fetch",lambda _:HTML); monkeypatch.setattr(service,"_robots_allowed",lambda _:True); monkeypatch.setattr("app.services.collection.validate_public_url",lambda x:x)
    article,changed=service.ingest_url(source,"https://news.example/story")
    assert changed and article.extraction_complete and len(article.versions)==1
    same,changed=service.ingest_url(source,"https://news.example/story")
    assert same.id==article.id and not changed and len(same.versions)==1
    monkeypatch.setattr(service,"_fetch",lambda _:HTML.replace("Evidence sentence.","Updated fact."))
    updated,changed=service.ingest_url(source,"https://news.example/story")
    assert changed and len(updated.versions)==2 and updated.current_hash!=article.versions[0].content_hash

def test_collection_advances_poll_time_when_every_article_is_unchanged(db,monkeypatch):
    source=Source(name="Example",url="https://news.example",topics=[]); db.add(source); db.commit()
    service=CollectionService(db)
    monkeypatch.setattr(service.settings,"crawl_delay_seconds",0)
    monkeypatch.setattr(service,"discover",lambda _:["https://news.example/story"])
    monkeypatch.setattr(service,"ingest_url",lambda *_:(object(),False))
    result=service.collect(source)
    assert result["unchanged"]==1
    assert source.last_collected_at is not None
