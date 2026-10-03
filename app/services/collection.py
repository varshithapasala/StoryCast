import hashlib, time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree
import feedparser, httpx, trafilatura
from dateutil.parser import parse as parse_date
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.entities import Article, ArticleVersion, Source
from app.repositories.repositories import ArticleRepository
from app.services.url_safety import validate_public_url

class SkippedArticle(ValueError): pass

class LinkParser(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href")
            if href: self.links.append(href)

class CollectionService:
    def __init__(self,db:Session): self.db=db; self.settings=get_settings()
    def _fetch(self,url:str)->str:
        safe=validate_public_url(url)
        with httpx.Client(timeout=self.settings.source_timeout_seconds,follow_redirects=False,headers={"User-Agent":self.settings.source_user_agent}) as client:
            response=client.get(safe); response.raise_for_status()
            if len(response.content)>self.settings.max_article_bytes: raise ValueError("Response exceeds size limit")
            return response.text
    def _robots_allowed(self,url:str)->bool:
        parsed=urlsplit(url); robots_url=f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            parser=RobotFileParser(); parser.set_url(robots_url); parser.parse(self._fetch(robots_url).splitlines()); return parser.can_fetch(self.settings.source_user_agent,url)
        except Exception: return True
    def _render_js(self,url:str)->str:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True,executable_path="/usr/bin/chromium" if __import__("os").path.exists("/usr/bin/chromium") else None)
            page=browser.new_page()
            def guard(route):
                try: validate_public_url(route.request.url); route.continue_()
                except Exception: route.abort()
            page.route("**/*",guard); page.goto(url,wait_until="networkidle",timeout=int(self.settings.source_timeout_seconds*1000)); content=page.content(); browser.close(); return content
    def discover(self,source:Source)->list[str]:
        candidates=[urljoin(source.url,p) for p in ("/feed","/rss","/rss.xml","/atom.xml")]
        if any(x in source.url.lower() for x in ("feed","rss","atom")): candidates.insert(0,source.url)
        for url in dict.fromkeys(candidates):
            try:
                feed=feedparser.parse(self._fetch(url))
                links=[str(e.link) for e in feed.entries if getattr(e,"link",None)]
                if links: return links[:50]
            except Exception: continue
        for sitemap_url in (urljoin(source.url,"/news-sitemap.xml"),urljoin(source.url,"/sitemap_news.xml")):
            try:
                root=ElementTree.fromstring(self._fetch(sitemap_url)); links=[node.text for node in root.iter() if node.tag.endswith("loc") and node.text]
                if links: return links[:50]
            except Exception: continue
        try:
            html=self._fetch(source.url); host=urlsplit(source.url).hostname
            try:
                from scrapy.http import HtmlResponse
                from scrapy.linkextractors import LinkExtractor
                response=HtmlResponse(url=source.url,body=html,encoding="utf-8"); raw_links=[link.url for link in LinkExtractor(allow_domains=[host]).extract_links(response)]
            except ImportError:
                parser=LinkParser(); parser.feed(html); raw_links=parser.links
            links=[]
            for raw in raw_links:
                link=urljoin(source.url,raw)
                if urlsplit(link).hostname==host and link not in links and link.rstrip("/")!=source.url.rstrip("/"): links.append(link)
            if links: return links[:25]
        except Exception: pass
        return [source.url]
    def ingest_url(self,source:Source,url:str,title_hint:str="")->tuple[Article,bool]:
        canonical=validate_public_url(url)
        if not self._robots_allowed(canonical): raise SkippedArticle("Blocked by publisher robots policy")
        html=self._fetch(canonical)
        text=trafilatura.extract(html,include_links=False,include_images=False,output_format="txt") or ""
        if len(text)<200 and source.render_javascript:
            html=self._render_js(canonical); text=trafilatura.extract(html,include_links=False,include_images=False,output_format="txt") or ""
        metadata=trafilatura.extract_metadata(html)
        title=(metadata.title if metadata else None) or title_hint or canonical
        declared=getattr(metadata,"url",None) if metadata else None
        if declared:
            try: canonical=validate_public_url(declared)
            except Exception: pass
        searchable=f"{title}\n{text}".lower()
        if source.topics and not any(topic.lower() in searchable for topic in source.topics): raise SkippedArticle("Article does not match configured topics")
        published=None
        if metadata and metadata.date:
            try:
                published=parse_date(metadata.date)
                if published.tzinfo is None: published=published.replace(tzinfo=timezone.utc)
                if published<datetime.now(timezone.utc)-timedelta(hours=self.settings.freshness_hours): raise SkippedArticle("Article is outside the freshness window")
            except SkippedArticle: raise
            except Exception: published=None
        digest=hashlib.sha256(text.encode()).hexdigest(); repo=ArticleRepository(self.db,source.owner_id); article=repo.by_url(canonical)
        if article and article.current_hash==digest: return article,False
        if not article:
            article=Article(source_id=source.id,canonical_url=canonical,title=title,current_hash=digest,extraction_complete=len(text)>=200,owner_id=source.owner_id,published_at=published)
            self.db.add(article); self.db.flush()
        else:
            article.current_hash=digest; article.title=title; article.extraction_complete=len(text)>=200; article.published_at=published or article.published_at
        version=ArticleVersion(article_id=article.id,content_hash=digest,text=text,metadata_json={"author":getattr(metadata,"author",None),"date":getattr(metadata,"date",None)})
        self.db.add(version); source.last_collected_at=datetime.now(timezone.utc); self.db.commit(); self.db.refresh(article); return article,True
    def collect(self,source:Source)->dict:
        created=0; unchanged=0; errors=[]
        for url in self.discover(source):
            try:
                _,changed=self.ingest_url(source,url); created+=int(changed); unchanged+=int(not changed)
            except SkippedArticle as exc: unchanged+=1
            except Exception as exc: errors.append({"url":url,"error":str(exc)})
            time.sleep(self.settings.crawl_delay_seconds)
        # Record the polling attempt even when every article was unchanged or
        # skipped. Otherwise the scheduler reuses the same completed dedupe key
        # and this source is never collected again.
        source.last_collected_at=datetime.now(timezone.utc)
        self.db.commit()
        return {"created_or_updated":created,"unchanged":unchanged,"errors":errors}
