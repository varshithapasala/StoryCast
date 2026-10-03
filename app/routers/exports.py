from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from urllib.parse import urlsplit
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.repositories import ExportRepository
from app.schemas.api import ExportRead
router=APIRouter(prefix="/exports",tags=["exports"])
@router.get("",response_model=list[ExportRead])
def exports(db:Session=Depends(get_db)): return ExportRepository(db).list()
@router.get("/{export_id}/download")
def download_export(export_id:str,db:Session=Depends(get_db)):
    export=ExportRepository(db).get(export_id)
    if not export: raise HTTPException(404,"Export not found")
    if export.video_path.startswith("s3://"):
        from app.core.config import get_settings
        from app.services.storage import S3Storage
        parsed=urlsplit(export.video_path); url=S3Storage().client.generate_presigned_url("get_object",Params={"Bucket":parsed.netloc,"Key":parsed.path.lstrip("/")},ExpiresIn=900)
        return RedirectResponse(url)
    path=Path(export.video_path).resolve()
    if not path.is_file(): raise HTTPException(404,"Export file is unavailable")
    return FileResponse(path,media_type="video/mp4",filename=f"storycast-{export.project_id}-v{export.project_version}.mp4")
