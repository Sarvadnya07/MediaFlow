import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
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
    In-process, SQLite-backed asynchronous queue manager with concurrency throttling,
    validated state transitions, crash recovery, and throttled event emissions.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_concurrent: int = 3,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        auto_start_scheduler: bool = True,
    ):
        self.max_concurrent = max_concurrent
        self.event_callback = event_callback
        self.lock = threading.RLock()
        self.running = True

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
        self.last_persist_time: Dict[str, float] = {}

        # Recover interrupted downloads from prior crashes/restarts
        self.recover_interrupted_jobs()

        # Background scheduling loop
        if auto_start_scheduler:
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, name="queue-scheduler", daemon=True)
            self.scheduler_thread.start()
        else:
            self.scheduler_thread = None

    def recover_interrupted_jobs(self):
        """Reset jobs left in transient states (analyzing, downloading, processing, verifying) back to queued."""
        with self.SessionLocal() as session:
            transient_states = [
                DownloadState.ANALYZING.value,
                DownloadState.DOWNLOADING.value,
                DownloadState.PROCESSING.value,
                DownloadState.VERIFYING.value,
            ]
            records = session.query(QueueItemRecord).filter(QueueItemRecord.state.in_(transient_states)).all()
            for r in records:
                logger.warning(f"Crash recovery: Job {r.id} found in '{r.state}', resetting to 'queued'.")
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
        playlist_id: Optional[str] = None,
        playlist_index: Optional[int] = None,
    ) -> QueueItem:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        item = QueueItem(
            id=job_id,
            url=url,
            title=title or "Queued Media",
            state=DownloadState.QUEUED,
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
            records = session.query(QueueItemRecord).order_by(QueueItemRecord.created_at.desc()).all()
            return [
                QueueItem(
                    id=r.id,
                    url=r.url,
                    title=r.title,
                    state=DownloadState(r.state),
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

    def cancel_job(self, job_id: str) -> bool:
        from ..services.yt_service import trigger_cancellation

        with self.lock:
            # Trigger in-flight download thread cooperative cancellation
            trigger_cancellation(job_id)

            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if not record:
                    return False

                current_state = DownloadState(record.state)
                if current_state not in (DownloadState.COMPLETED, DownloadState.CANCELLED):
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
                if current_state in (DownloadState.FAILED, DownloadState.CANCELLED):
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
        """Continuously inspect queued jobs and dispatch them according to max_concurrent quota."""
        while self.running:
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
                    .order_by(QueueItemRecord.created_at.asc())
                    .limit(available_slots)
                    .all()
                )

                for r in queued_records:
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
                    }

                    t = threading.Thread(
                        target=self._run_job_worker,
                        args=(job_dict,),
                        name=f"worker-{r.id}",
                        daemon=True,
                    )
                    self.active_jobs[r.id] = t
                    t.start()
                    self._emit_event("job_state_changed", {"job_id": r.id, "state": "downloading"})

    def _run_job_worker(self, job_dict: Dict[str, Any]):
        from ..services.yt_service import download_stream, DownloadCancelledError

        job_id = job_dict["id"]
        url = job_dict["url"]
        format_id = job_dict.get("format_id")
        quality = job_dict.get("quality")
        subtitle_lang = job_dict.get("subtitle_lang")
        output_dir = job_dict.get("output_dir") or str(settings.DOWNLOADS_DIR)

        def on_progress(p_data: Dict[str, Any]):
            # Throttle database writes (at most once every 1.0s per job)
            now = time.time()
            last_persist = self.last_persist_time.get(job_id, 0.0)
            should_persist = (now - last_persist) >= 1.0 or p_data.get("percent", 0) >= 99.0

            if should_persist:
                self.last_persist_time[job_id] = now
                with self.SessionLocal() as session:
                    record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                    if record and record.state == DownloadState.DOWNLOADING.value:
                        record.percent = p_data.get("percent", record.percent)
                        record.downloaded_bytes = p_data.get("downloaded_bytes", record.downloaded_bytes)
                        record.total_bytes = p_data.get("total_bytes", record.total_bytes)
                        record.speed = p_data.get("speed", record.speed)
                        record.eta = p_data.get("eta", record.eta)
                        record.updated_at = now
                        session.commit()

            # Emit real-time visual progress event to UI
            self._emit_event("progress", p_data)

        try:
            res = download_stream(
                url=url,
                output_dir=output_dir,
                job_id=job_id,
                format_id=format_id,
                quality=quality,
                subtitle_lang=subtitle_lang,
                progress_callback=on_progress,
                allow_private=True,
            )

            # Transition to COMPLETED
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record:
                    record.state = DownloadState.COMPLETED.value
                    record.percent = 100.0
                    record.title = res.get("title", record.title)
                    record.filepath = res.get("filepath")
                    record.updated_at = time.time()
                    session.commit()

            self._emit_event("job_completed", {"job_id": job_id, "filepath": res.get("filepath")})

        except DownloadCancelledError:
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record:
                    record.state = DownloadState.CANCELLED.value
                    record.updated_at = time.time()
                    session.commit()
            self._emit_event("job_state_changed", {"job_id": job_id, "state": "cancelled"})

        except Exception as exc:
            logger.error(f"Job {job_id} failed: {exc}", exc_info=True)
            with self.SessionLocal() as session:
                record = session.query(QueueItemRecord).filter(QueueItemRecord.id == job_id).first()
                if record:
                    record.state = DownloadState.FAILED.value
                    record.error_message = str(exc)
                    record.updated_at = time.time()
                    session.commit()
            self._emit_event("job_failed", {"job_id": job_id, "error": str(exc)})

        finally:
            with self.lock:
                self.active_jobs.pop(job_id, None)

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        if self.event_callback:
            try:
                self.event_callback({"type": "event", "event": event_type, "data": data})
            except Exception:
                pass

    def shutdown(self):
        self.running = False
