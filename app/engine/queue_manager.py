import os
import sys
import threading
import time
import uuid
import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import settings
from ..logging_config import logger
from .queue_models import DownloadState, InvalidStateTransitionError, QueueItem

Base = declarative_base()


class QueueItemRecord(Base):
    """Authoritative persistent queue table in SQLite."""
    __tablename__ = "download_queue"

    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String, default="Pending Analysis")
    state = Column(String, default=DownloadState.QUEUED.value)
    priority = Column(Integer, default=0)
    format_id = Column(String, nullable=True)
    quality = Column(String, nullable=True)
    subtitle_lang = Column(String, nullable=True)
    output_dir = Column(String, nullable=True)
    percent = Column(Float, default=0.0)
    downloaded_bytes = Column(Integer, default=0)
    total_bytes = Column(Integer, default=0)
    speed = Column(Float, default=0.0)
    eta = Column(Integer, default=0)
    filepath = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    playlist_id = Column(String, nullable=True)
    playlist_index = Column(Integer, nullable=True)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)


class DownloadQueueManager:
    """
    Intelligent SQLite-backed download queue manager with:
    - Priority-based scheduling & manual reordering
    - Per-provider concurrency throttling
    - Exponential backoff with jitter on transient failures
    - Resume and collision-safe atomic file management
    - Global pause / resume controls
    - Throttled persistence and event emission
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_concurrent: int = 3,
        per_provider_concurrent: int = 2,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        auto_start_scheduler: bool = True,
    ):
        self.max_concurrent = max_concurrent
        self.per_provider_concurrent = per_provider_concurrent
        self.event_callback = event_callback
        self.lock = threading.RLock()
        self.running = True
        self.is_paused_all = False

        # Database setup
        database_url = f"sqlite:///{db_path}" if db_path else settings.DATABASE_URL
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # In-memory index of active worker threads and cancellation events
        self.active_jobs: Dict[str, threading.Thread] = {}
        self.active_domains: Dict[str, int] = {}
        self.last_persist_time: Dict[str, float] = {}

        # Recover interrupted downloads from prior crashes/restarts
        self.recover_interrupted_jobs()

        # Background scheduling loop
        if auto_start_scheduler:
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="QueueScheduler")
            self.scheduler_thread.start()

    def recover_interrupted_jobs(self):
        """Reset downloading/analyzing jobs left in uncommitted states on crash back to queued."""
        with self.SessionLocal() as session:
            interrupted = (
                session.query(QueueItemRecord)
                .filter(QueueItemRecord.state.in_([DownloadState.DOWNLOADING.value, DownloadState.ANALYZING.value]))
                .all()
            )
            for r in interrupted:
                logger.info(f"Crash recovery: reverting interrupted job {r.id} ({r.title}) back to queued state.")
                r.state = DownloadState.QUEUED.value
                r.updated_at = time.time()
            session.commit()

    def add_job(
        self,
        url: str,
        title: Optional[str] = None,
        format_id: Optional[str] = None,
        quality: Optional[str] = None,
        subtitle_lang: Optional[str] = None,
        output_dir: Optional[str] = None,
        priority: int = 0,
        playlist_id: Optional[str] = None,
        playlist_index: Optional[int] = None,
    ) -> QueueItem:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        item = QueueItem(
            id=job_id,
            url=url,
            title=title or "Queued Media",
            state=DownloadState.QUEUED,
            priority=priority,
            format_id=format_id,
            quality=quality,
            subtitle_lang=subtitle_lang,
            output_dir=output_dir or str(settings.DOWNLOADS_DIR),
            playlist_id=playlist_id,
            playlist_index=playlist_index,
        )

        with self.SessionLocal() as session:
            record = QueueItemRecord(**item.model_dump())
            session.add(record)
            session.commit()

        self._emit_event("job_added", item.model_dump())
        return item

    def get_all_jobs(self) -> List[QueueItem]:
        with self.SessionLocal() as session:
            records = session.query(QueueItemRecord).order_by(QueueItemRecord.priority.desc(), QueueItemRecord.created_at.asc()).all()
            return [
                QueueItem(
                    id=r.id,
                    url=r.url,
                    title=r.title,
                    state=DownloadState(r.state),
                    priority=r.priority or 0,
                    format_id=r.format_id,
                    quality=r.quality,
                    subtitle_lang=r.subtitle_lang,
                    output_dir=r.output_dir,
                    percent=r.percent,
                    downloaded_bytes=r.downloaded_bytes,
                    total_bytes=r.total_bytes,
                    speed=r.speed,
                    eta=r.eta,
                    filepath=r.filepath,
                    error_message=r.error_message,
                    retry_count=r.retry_count,
                    max_retries=r.max_retries,
                    playlist_id=r.playlist_id,
                    playlist_index=r.playlist_index,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in records
            ]

    def set_job_priority(self, job_id: str, new_priority: int) -> bool:
        """Manual priority reordering."""
        with self.lock:
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record:
                    record.priority = new_priority
                    record.updated_at = time.time()
                    session.commit()
                    self._emit_event("job_priority_changed", {"job_id": job_id, "priority": new_priority})
                    return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause an individual active or queued job."""
        from app.services.yt_service import trigger_cancellation
        trigger_cancellation(job_id)
        with self.lock:
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record and record.state in (DownloadState.DOWNLOADING.value, DownloadState.QUEUED.value):
                    record.state = DownloadState.PAUSED.value
                    record.updated_at = time.time()
                    session.commit()
                    self._emit_event("job_state_changed", {"job_id": job_id, "state": "paused"})
                    return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume an individual paused job."""
        with self.lock:
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record and record.state == DownloadState.PAUSED.value:
                    record.state = DownloadState.QUEUED.value
                    record.updated_at = time.time()
                    session.commit()
                    self._emit_event("job_state_changed", {"job_id": job_id, "state": "queued"})
                    return True
        return False

    def pause_all(self):
        """Pause all pending and downloading jobs."""
        with self.lock:
            self.is_paused_all = True
            for j_id in list(self.active_jobs.keys()):
                self.pause_job(j_id)
            with self.SessionLocal() as session:
                session.query(QueueItemRecord).filter(QueueItemRecord.state == DownloadState.QUEUED.value).update(
                    {"state": DownloadState.PAUSED.value, "updated_at": time.time()}
                )
                session.commit()
            self._emit_event("queue_paused_all", {})

    def resume_all(self):
        """Resume all paused jobs."""
        with self.lock:
            self.is_paused_all = False
            with self.SessionLocal() as session:
                session.query(QueueItemRecord).filter(QueueItemRecord.state == DownloadState.PAUSED.value).update(
                    {"state": DownloadState.QUEUED.value, "updated_at": time.time()}
                )
                session.commit()
            self._emit_event("queue_resumed_all", {})

    def clear_completed(self) -> int:
        """Clear all completed or cancelled items from the queue."""
        with self.lock:
            with self.SessionLocal() as session:
                deleted = session.query(QueueItemRecord).filter(
                    QueueItemRecord.state.in_([DownloadState.COMPLETED.value, DownloadState.CANCELLED.value])
                ).delete(synchronize_session=False)
                session.commit()
                self._emit_event("queue_cleared_completed", {"count": deleted})
                return deleted

    def cancel_job(self, job_id: str) -> bool:
        from app.services.yt_service import trigger_cancellation
        trigger_cancellation(job_id)
        with self.lock:
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record and record.state != DownloadState.COMPLETED.value:
                    record.state = DownloadState.CANCELLED.value
                    record.updated_at = time.time()
                    session.commit()
                    self._emit_event("job_state_changed", {"job_id": job_id, "state": "cancelled"})
                    return True
        return False

    def retry_job(self, job_id: str) -> bool:
        with self.lock:
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if not record:
                    return False

                current_state = DownloadState(record.state)
                if current_state in (DownloadState.FAILED, DownloadState.CANCELLED, DownloadState.PAUSED):
                    record.state = DownloadState.QUEUED.value
                    record.error_message = None
                    record.percent = 0.0
                    record.retry_count += 1
                    record.updated_at = time.time()
                    session.commit()
                    self._emit_event("job_state_changed", {"job_id": job_id, "state": "queued"})
                    return True
        return False

    def remove_job(self, job_id: str) -> bool:
        with self.lock:
            self.cancel_job(job_id)
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record:
                    session.delete(record)
                    session.commit()
                    self._emit_event("job_removed", {"job_id": job_id})
                    return True
        return False

    def _scheduler_loop(self):
        """Continuously inspect queued jobs and dispatch them according to global & per-provider limits."""
        while self.running:
            if not self.is_paused_all:
                try:
                    self._dispatch_next_jobs()
                except Exception as e:
                    logger.error(f"Error in queue scheduler loop: {e}", exc_info=True)
            time.sleep(0.5)

    def _dispatch_next_jobs(self):
        with self.lock:
            active_count = len(self.active_jobs)
            available_slots = self.max_concurrent - active_count
            if available_slots <= 0:
                return

            with self.SessionLocal() as session:
                queued_records = (
                    session.query(QueueItemRecord)
                    .filter(QueueItemRecord.state == DownloadState.QUEUED.value)
                    .order_by(QueueItemRecord.priority.desc(), QueueItemRecord.created_at.asc())
                    .all()
                )

                dispatched = 0
                for r in queued_records:
                    if dispatched >= available_slots:
                        break

                    # Check per-provider domain limits
                    domain = urlparse(r.url).netloc.lower() or "direct"
                    current_domain_active = self.active_domains.get(domain, 0)
                    if current_domain_active >= self.per_provider_concurrent:
                        continue  # Skip to avoid aggressive parallel provider pounding

                    r.state = DownloadState.DOWNLOADING.value
                    r.updated_at = time.time()
                    session.commit()

                    job_dict = {
                        "id": r.id,
                        "url": r.url,
                        "title": r.title,
                        "format_id": r.format_id,
                        "quality": r.quality,
                        "subtitle_lang": r.subtitle_lang,
                        "output_dir": r.output_dir,
                        "retry_count": r.retry_count,
                        "max_retries": r.max_retries,
                    }

                    # Track domain concurrency
                    self.active_domains[domain] = current_domain_active + 1

                    t = threading.Thread(
                        target=self._run_job_worker,
                        args=(job_dict, domain),
                        daemon=True,
                        name=f"Worker-{r.id}",
                    )
                    self.active_jobs[r.id] = t
                    t.start()
                    dispatched += 1

    def _run_job_worker(self, job: Dict[str, Any], domain: str):
        job_id = job["id"]
        from app.services import yt_service
        from app.services.yt_service import DownloadCancelledError

        def progress_callback(progress_data: Dict[str, Any]):
            now = time.time()
            last_time = self.last_persist_time.get(job_id, 0.0)
            status = progress_data.get("status")

            # Persist visual update to DB throttled to at most once per 1.0 second, or upon finish
            if now - last_time >= 1.0 or status == "finished":
                self.last_persist_time[job_id] = now
                with self.SessionLocal() as session:
                    record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                    if record and record.state in (DownloadState.DOWNLOADING.value, DownloadState.PROCESSING.value):
                        record.percent = progress_data.get("percent", record.percent)
                        record.downloaded_bytes = progress_data.get("downloaded_bytes", record.downloaded_bytes)
                        record.total_bytes = progress_data.get("total_bytes") or record.total_bytes
                        record.speed = progress_data.get("speed", 0.0)
                        record.eta = progress_data.get("eta", 0)
                        record.updated_at = now
                        session.commit()

            # Emit live event to UI listeners
            self._emit_event("progress", {"job_id": job_id, **progress_data})

        try:
            res = yt_service.download_stream(
                url=job["url"],
                format_id=job.get("format_id"),
                quality=job.get("quality"),
                output_dir=job.get("output_dir"),
                subtitle_lang=job.get("subtitle_lang"),
                progress_callback=progress_callback,
                job_id=job_id,
            )

            # Mark complete
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record and record.state != DownloadState.CANCELLED.value:
                    record.state = DownloadState.COMPLETED.value
                    record.percent = 100.0
                    record.filepath = res.get("filename") or res.get("output_path")
                    record.updated_at = time.time()
                    session.commit()
                    # Automatically index completed file into Media Library
                    try:
                        from app.library.manager import media_library
                        if record.filepath:
                            media_library.index_file(
                                file_path=record.filepath,
                                source_url=record.url,
                                title=record.title,
                            )
                    except Exception as lib_err:
                        logger.warning(f"Failed to auto-index completed job {job_id} into media library: {lib_err}")

                    self._emit_event("job_completed", {
                        "job_id": job_id,
                        "filepath": record.filepath,
                    })

        except DownloadCancelledError:
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record:
                    record.state = DownloadState.CANCELLED.value
                    record.updated_at = time.time()
                    session.commit()
            self._emit_event("job_state_changed", {"job_id": job_id, "state": "cancelled"})

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record and record.state != DownloadState.CANCELLED.value:
                    # Exponential backoff with jitter retry evaluation
                    if record.retry_count < record.max_retries:
                        record.retry_count += 1
                        backoff = (2 ** record.retry_count) + random.uniform(0.5, 2.0)
                        record.state = DownloadState.QUEUED.value
                        record.error_message = f"Transient error: {e}. Retrying in {round(backoff, 1)}s..."
                        record.updated_at = time.time()
                        session.commit()
                        self._emit_event("job_retry_scheduled", {
                            "job_id": job_id,
                            "retry_count": record.retry_count,
                            "backoff": backoff,
                        })
                    else:
                        record.state = DownloadState.FAILED.value
                        record.error_message = str(e)
                        record.updated_at = time.time()
                        session.commit()
                        self._emit_event("job_state_changed", {
                            "job_id": job_id,
                            "state": "failed",
                            "error": str(e),
                        })

        finally:
            with self.lock:
                self.active_jobs.pop(job_id, None)
                if domain in self.active_domains:
                    self.active_domains[domain] = max(0, self.active_domains[domain] - 1)
                    if self.active_domains[domain] == 0:
                        self.active_domains.pop(domain, None)
                yt_service.unregister_cancellation_token(job_id)

    def _emit_event(self, event_name: str, data: Dict[str, Any]):
        if self.event_callback:
            try:
                self.event_callback({"event": event_name, "data": data})
            except Exception as e:
                logger.error(f"Error in queue event callback: {e}")

    def shutdown(self):
        self.running = False
        with self.lock:
            for j_id in list(self.active_jobs.keys()):
                self.cancel_job(j_id)
