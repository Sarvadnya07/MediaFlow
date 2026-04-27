import yt_dlp
import os
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Download, User
from ..schemas import DownloadResponse

from ..config import settings

DOWNLOADS_DIR = str(settings.DOWNLOADS_DIR.absolute())


from typing import List, Callable

def download_video_file(url: str, quality: str | None = None, progress_hooks: List[Callable] = None) -> tuple[str, str, str | None]:
    format_spec = "bestvideo+bestaudio/best"
    if quality and quality.endswith("p"):
        height = quality[:-1]
        format_spec = f"bestvideo[height<={height}]+bestaudio/best"

    ydl_opts = {
        "outtmpl": os.path.join(DOWNLOADS_DIR, "%(title)s.%(ext)s"),
        "format": format_spec,
        "merge_output_format": "mp4",
        "progress_hooks": progress_hooks or [],
        "writethumbnail": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "unknown")
        filename = ydl.prepare_filename(info)
        
        # Get thumbnail path
        thumbnail = None
        if "thumbnails" in info and len(info["thumbnails"]) > 0:
            # yt-dlp saves thumbnail with same name as video but different extension
            base, _ = os.path.splitext(filename)
            for ext in [".jpg", ".png", ".webp", ".jpeg"]:
                thumb_candidate = base + ext
                if os.path.exists(thumb_candidate):
                    thumbnail = thumb_candidate
                    break

    if not os.path.exists(filename):
        base, _ = os.path.splitext(filename)
        for ext in [".mp4", ".mkv", ".webm"]:
            candidate = base + ext
            if os.path.exists(candidate):
                filename = candidate
                break

    return title, filename, thumbnail


def download_video(url: str, quality: str, db: Session, user_id: int):
    try:
        title, filename, thumbnail = download_video_file(url, quality)

        download_entry = Download(
            url=url,
            title=title,
            filepath=filename,
            thumbnail_path=thumbnail,
            status="success",
            progress=100,
            created_at=datetime.utcnow(),
            user_id=user_id,
        )
        db.add(download_entry)
        db.commit()
        db.refresh(download_entry)

        return {"msg": "Download successful", "download": DownloadResponse(
            id=download_entry.id,
            url=download_entry.url,
            title=download_entry.title or "",
            filepath=download_entry.filepath or "",
            thumbnail_path=download_entry.thumbnail_path,
            status=download_entry.status,
            progress=download_entry.progress,
            error_message=download_entry.error_message,
            created_at=str(download_entry.created_at)
        )}

    except Exception as e:
        download_entry = Download(
            url=url,
            title="failed",
            filepath="",
            status="failed",
            created_at=datetime.utcnow(),
            user_id=user_id,
        )
        db.add(download_entry)
        db.commit()
        raise Exception(f"Download failed: {str(e)}")


def get_downloads(db_session: Session, user: User) -> list[DownloadResponse]:
    """
    Fetch downloads as DownloadResponse models.
    Admins see all downloads; users see only their own.
    """
    if user.role == "admin":
        entries = db_session.query(Download).all()
    else:
        entries = db_session.query(Download).filter(Download.user_id == user.id).all()
    return [
        DownloadResponse(
            id=e.id,
            url=e.url,
            title=e.title or "",
            filepath=e.filepath or "",
            thumbnail_path=e.thumbnail_path,
            summary=e.summary,
            tags=e.tags,
            status=e.status,
            progress=e.progress,
            error_message=e.error_message,
            created_at=str(e.created_at),
        )
        for e in entries
    ]
