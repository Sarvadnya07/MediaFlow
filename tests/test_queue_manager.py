import pytest
import time
from app.engine.queue_models import DownloadState, InvalidStateTransitionError, QueueItem
from app.engine.queue_manager import DownloadQueueManager


def test_queue_state_transitions():
    item = QueueItem(id="test-job-1", url="https://example.com/video")
    assert item.state == DownloadState.QUEUED

    # Valid transitions
    item.transition_to(DownloadState.DOWNLOADING)
    assert item.state == DownloadState.DOWNLOADING

    item.transition_to(DownloadState.PROCESSING)
    assert item.state == DownloadState.PROCESSING

    item.transition_to(DownloadState.VERIFYING)
    assert item.state == DownloadState.VERIFYING

    item.transition_to(DownloadState.COMPLETED)
    assert item.state == DownloadState.COMPLETED

    # Reject invalid transition from completed
    with pytest.raises(InvalidStateTransitionError):
        item.transition_to(DownloadState.DOWNLOADING)


def test_queue_manager_crud_and_retry(tmp_path):
    db_file = tmp_path / "queue_test.db"
    events = []

    mgr = DownloadQueueManager(
        db_path=str(db_file),
        max_concurrent=2,
        event_callback=lambda evt: events.append(evt)
    )

    try:
        # Add job
        job = mgr.add_job("https://example.com/media1", title="Media 1")
        assert job.id.startswith("job-")

        all_jobs = mgr.get_all_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0].title == "Media 1"

        # Cancel job
        cancelled = mgr.cancel_job(job.id)
        assert cancelled is True

        all_jobs = mgr.get_all_jobs()
        assert all_jobs[0].state == DownloadState.CANCELLED

        # Retry job
        retried = mgr.retry_job(job.id)
        assert retried is True

        all_jobs = mgr.get_all_jobs()
        assert all_jobs[0].state == DownloadState.QUEUED
        assert all_jobs[0].retry_count == 1

        # Remove job
        removed = mgr.remove_job(job.id)
        assert removed is True
        assert len(mgr.get_all_jobs()) == 0

    finally:
        mgr.shutdown()


def test_queue_manager_crash_recovery(tmp_path):
    db_file = tmp_path / "recovery_test.db"

    # Create manager and add job directly in downloading state
    mgr1 = DownloadQueueManager(db_path=str(db_file), max_concurrent=2, auto_start_scheduler=False)
    job = mgr1.add_job("https://example.com/media_crash", title="Crash Test")

    with mgr1.SessionLocal() as session:
        from app.engine.queue_manager import QueueItemRecord
        rec = session.query(QueueItemRecord).filter(QueueItemRecord.id == job.id).first()
        rec.state = DownloadState.DOWNLOADING.value
        session.commit()

    mgr1.shutdown()

    # Re-instantiate manager (simulating application restart after unexpected shutdown)
    mgr2 = DownloadQueueManager(db_path=str(db_file), max_concurrent=2, auto_start_scheduler=False)
    try:
        jobs = mgr2.get_all_jobs()
        # Should have automatically recovered to QUEUED
        assert jobs[0].state == DownloadState.QUEUED
    finally:
        mgr2.shutdown()
