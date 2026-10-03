from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import Base, engine
from app.routers import articles, exports, jobs, projects, sources

s=get_settings(); s.storage_root.mkdir(parents=True,exist_ok=True)
if s.database_url.startswith("sqlite"): Base.metadata.create_all(engine)
app=FastAPI(title=s.app_name,version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in s.cors_origins.split(",") if x.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
for router in (sources.router,articles.router,projects.router,jobs.router,exports.router): app.include_router(router,prefix=s.api_prefix)
@app.get("/health")
def health(): return {"status":"ok"}
