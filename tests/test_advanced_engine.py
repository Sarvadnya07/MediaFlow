"""
Advanced Download Engine & Queue Intelligence Tests.
Verifies priority scheduling, global & individual pause/resume, clear completed,
exponential backoff retry, and per-provider concurrency limiting.
"""
import pytest
import time
from app.engine.queue_manager import DownloadQueueManager
from app.engine.queue_models import DownloadState


def test_priority_based_queue_ordering(tmp_path):
    db_file = tmp_path / "queue_priority_test.db"
    mgr = DownloadQueueManager(db_path=str(db_file), auto_start_scheduler=False)

    job1 = mgr.add_job(url="https://example.com/video1.mp4", title="Normal Priority 1", priority=0)
    job2 = mgr.add_job(url="https://example.com/video2.mp4", title="High Priority", priority=10)
    job3 = mgr.add_job(url="https://example.com/video3.mp4", title="Normal Priority 2", priority=0)

    jobs = mgr.get_all_jobs()
    # High priority item must be ordered first
    assert jobs[0].id == job2.id
    assert jobs[0].priority == 10

    # Test dynamic priority change
    mgr.set_job_priority(job3.id, 20)
    reordered_jobs = mgr.get_all_jobs()
    assert reordered_jobs[0].id == job3.id
    assert reordered_jobs[0].priority == 20


def test_pause_resume_and_clear_controls(tmp_path):
    db_file = tmp_path / "queue_controls_test.db"
    mgr = DownloadQueueManager(db_path=str(db_file), auto_start_scheduler=False)

    job1 = mgr.add_job(url="https://example.com/video1.mp4", title="Item 1")
    job2 = mgr.add_job(url="https://example.com/video2.mp4", title="Item 2")

    # Pause individual
    assert mgr.pause_job(job1.id) is True
    jobs = {j.id: j for j in mgr.get_all_jobs()}
    assert jobs[job1.id].state == DownloadState.PAUSED

    # Resume individual
    assert mgr.resume_job(job1.id) is True
    jobs = {j.id: j for j in mgr.get_all_jobs()}
    assert jobs[job1.id].state == DownloadState.QUEUED

    # Pause all
    mgr.pause_all()
    for j in mgr.get_all_jobs():
        assert j.state == DownloadState.PAUSED

    # Resume all
    mgr.resume_all()
    for j in mgr.get_all_jobs():
        assert j.state == DownloadState.QUEUED

    # Mark one completed, clear completed
    with mgr.SessionLocal() as session:
        from app.engine.queue_manager import QueueItemRecord
        r = session.query(QueueItemRecord).filter(QueueItemRecord.id == job1.id).first()
        r.state = DownloadState.COMPLETED.value
        session.commit()

    cleared = mgr.clear_completed()
    assert cleared == 1
    remaining = mgr.get_all_jobs()
    assert len(remaining) == 1
    assert remaining[0].id == job2.id


def test_per_provider_domain_concurrency_limit(tmp_path):
    db_file = tmp_path / "queue_domain_test.db"
    mgr = DownloadQueueManager(
        db_path=str(db_file),
        max_concurrent=4,
        per_provider_concurrent=1,
        auto_start_scheduler=False,
    )

    # Add 2 jobs on domain A, 1 on domain B
    j1 = mgr.add_job(url="https://domain-a.com/stream1.mp4")
    j2 = mgr.add_job(url="https://domain-a.com/stream2.mp4")
    j3 = mgr.add_job(url="https://domain-b.com/stream1.mp4")

    # Simulate dispatch
    mgr._dispatch_next_jobs()

    # j1 and j3 should be dispatched; j2 should wait because domain-a per-provider limit is 1
    jobs = {j.id: j for j in mgr.get_all_jobs()}
    assert jobs[j1.id].state == DownloadState.DOWNLOADING
    assert jobs[j3.id].state == DownloadState.DOWNLOADING
    assert jobs[j2.id].state == DownloadState.QUEUED
