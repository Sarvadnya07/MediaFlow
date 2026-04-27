from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..models import Download
from ..database import get_db
from ..auth import get_current_user
from ..schemas import DownloadRequest, DownloadResponse, ConvertRequest, MetadataRequest
from ..services import yt_service, ffmpeg_service
from ..worker.tasks import download_task

router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.post("/", response_model=StartDownloadResponse)
def start_download(
    req: DownloadRequest,
    db_session: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Start a YouTube/video download job for the authenticated user.
    """
    try:
        new_download = Download(
            url=req.url,
            status="PENDING",
            user_id=current_user.id,
            webhook_url=req.webhook_url,
        )
        db_session.add(new_download)
        db_session.commit()
        db_session.refresh(new_download)

        download_task.delay(new_download.id, req.url, req.quality)

        return {"job_id": new_download.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{download_id}", response_model=DownloadResponse)
def get_download_status(
    download_id: int,
    db_session: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Check the status and progress of a specific download job.
    """
    query = db_session.query(Download).filter(Download.id == download_id)
    if current_user.role != "admin":
        query = query.filter(Download.user_id == current_user.id)
        
    download = query.first()
    
    if not download:
        raise HTTPException(status_code=404, detail="Download job not found")
        
    return DownloadResponse(
        id=download.id,
        url=download.url,
        title=download.title or "",
        filepath=download.filepath or "",
        thumbnail_path=download.thumbnail_path,
        summary=download.summary,
        tags=download.tags,
        status=download.status,
        progress=download.progress,
        error_message=download.error_message,
        created_at=str(download.created_at)
    )


@router.get("/", response_model=List[DownloadResponse])
def get_all_downloads(
    db_session: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Retrieve all downloads belonging to the authenticated user.
    """
    try:
        return yt_service.get_downloads(db_session, current_user)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/convert", response_model=ConversionResponse)
def convert_file(req: ConvertRequest):
    """
    Convert an existing file to another audio format (via ffmpeg).
    """
    try:
        output = ffmpeg_service.convert_to_audio(req.file, req.format)
        return {"status": "success", "output_file": output}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/metadata", response_model=ConversionResponse)
def add_metadata(req: MetadataRequest):
    """
    Embed metadata (title, artist, thumbnail) into an audio/video file.
    """
    try:
        output = ffmpeg_service.embed_metadata(
            req.file,
            title=req.title,
            artist=req.artist,
            thumbnail=req.thumbnail,
        )
        return {"status": "success", "output_file": output}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
