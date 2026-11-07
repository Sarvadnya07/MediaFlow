from app.database import SessionLocal
from app.models import Download
from app.services.yt_service import download_video_file
from app.services.ai_service import ai_service
from .celery_app import celery
from ..logging_config import logger
from ..config import settings
import requests
import redis
import json


@celery.task(bind=True)
def download_task(self, download_id: int, url: str, quality: str | None):
    db = SessionLocal()
    download = None

    logger.info(f"Received download task: {download_id} | URL: {url}")
    try:
        download = db.get(Download, download_id)
        if not download:
            logger.warning(f"Download ID {download_id} not found in database")
            return

        redis_client = redis.from_url(settings.REDIS_URL)

        download.status = "PROCESSING"
        db.commit()
        
        redis_client.publish(
            f"download_progress:{download_id}",
            json.dumps({"progress": 0, "status": "PROCESSING"})
        )

        def progress_hook(d):
            if d["status"] == "downloading":
                p = d.get("_percent_str", "0%").replace("%", "").strip()
                try:
                    progress_int = int(float(p))
                    download.progress = progress_int
                    db.commit()
                    redis_client.publish(
                        f"download_progress:{download_id}",
                        json.dumps({"progress": progress_int, "status": "PROCESSING"})
                    )
                except Exception:
                    pass

        title, file_path, thumb_path, description, duration = download_video_file(url, quality, progress_hooks=[progress_hook])

        download.status = "COMPLETED"
        download.progress = 100
        download.title = title
        download.thumbnail_path = thumb_path
        download.description = description
        download.duration = duration
        download.filepath = file_path
        
        # AI-Powered Metadata Generation
        try:
            download.summary = ai_service.summarize_video(title, description)
            tags = ai_service.generate_tags(title)
            download.tags = ", ".join(tags)
        except Exception as ai_err:
            logger.error(f"AI enrichment failed for {download_id}: {str(ai_err)}")

        db.commit()
        redis_client.publish(
            f"download_progress:{download_id}",
            json.dumps({"progress": 100, "status": "COMPLETED"})
        )
        
        logger.info(f"Task {download_id} COMPLETED: {title}")
        
        # Notify via webhook
        notify_webhook(download)
    except Exception as e:
        logger.error(f"Task {download_id} FAILED: {str(e)}", exc_info=True)
        if download is not None:
            download.status = "FAILED"
            download.error_message = str(e)
            db.commit()
            redis_client.publish(
                f"download_progress:{download_id}",
                json.dumps({"progress": download.progress, "status": "FAILED", "error": str(e)})
            )
            notify_webhook(download)
        raise
    finally:
        db.close()

def notify_webhook(download: Download):
    if not download.webhook_url:
        return
    
    payload = {
        "job_id": download.id,
        "status": download.status,
        "url": download.url,
        "title": download.title,
        "filepath": download.filepath,
        "thumbnail_path": download.thumbnail_path,
        "error_message": download.error_message,
        "progress": download.progress
    }
    
    try:
        requests.post(download.webhook_url, json=payload, timeout=5)
    except Exception:
        pass  # Fail silently for webhooks
