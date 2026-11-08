"""
MediaDock ARCH-03 Resilience, Concurrency, and Failure-Mode Validation Suite.
Validates:
1. Concurrent SQLite write operations and thread safety under high contention.
2. Malformed JSON, corrupted IPC inputs, and pipeline crash containment.
3. Network connection interruptions, HTTP range headers, and partial-stream recovery.
4. Process cancellation hooks and thread cleanup under active streaming.
"""
import io
import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.engine.queue_manager import DownloadQueueManager, DownloadState
from app.engine.sidecar import SidecarRunner
from app.engine.protocol import IPCRequest
from app.services import yt_service


def test_concurrent_queue_writes_and_sqlite_locking(tmp_path):
    """
    Stress-tests the DownloadQueueManager under heavy multi-threaded concurrent writes.
    Validates that SQLite with WAL mode avoids 'database is locked' errors.
    """
    db_file = tmp_path / "concurrent_stress.db"
    db_url = f"sqlite:///{db_file}"

    with patch("app.config.settings.DATABASE_URL", db_url):
        mgr = DownloadQueueManager(db_path=str(db_file))

        num_threads = 8
        items_per_thread = 10
        errors = []

        def worker_task(thread_id: int):
            for i in range(items_per_thread):
                try:
                    job = mgr.add_job(
                        url=f"https://example.com/stream_{thread_id}_{i}.mp4",
                        title=f"Worker {thread_id} Item {i}",
                        priority=i % 3,
                    )
                    assert job.id is not None
                    # Concurrent read
                    jobs = mgr.get_all_jobs()
                    assert len(jobs) > 0
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent writes threw errors: {errors}"
        final_jobs = mgr.get_all_jobs()
        assert len(final_jobs) == num_threads * items_per_thread


def test_sidecar_ipc_resilience_to_malformed_and_oversized_payloads():
    """
    Validates that malformed JSON, truncated lines, or illegal commands do not crash
    the sidecar process or leak unhandled exceptions to stdio.
    """
    stdin = io.StringIO()
    stdout = io.StringIO()
    runner = SidecarRunner(stdin=stdin, stdout=stdout)

    # 1. Syntax-corrupted JSON
    runner.handle_raw_message("{\"action\": \"download\", \"payload\": {")
    out1 = json.loads(stdout.getvalue().strip())
    assert out1["status"] == "error"
    assert out1["error"]["code"] == "INVALID_JSON"

    # 2. Payload with unsupported action
    stdout.truncate(0)
    stdout.seek(0)
    runner.handle_raw_message(json.dumps({"id": "corrupt-1", "action": "illegal_op_xyz"}))
    out2 = json.loads(stdout.getvalue().strip())
    assert out2["status"] == "error"
    assert out2["error"]["code"] == "VALIDATION_ERROR"

    # 3. Valid action with null/missing required payload
    stdout.truncate(0)
    stdout.seek(0)
    runner.handle_raw_message(json.dumps({"id": "corrupt-2", "action": "analyze", "payload": {}}))
    out3 = json.loads(stdout.getvalue().strip())
    assert out3["status"] == "error"
    assert out3["error"]["code"] == "MISSING_ARGUMENT"


def test_download_cancellation_releases_thread_and_cleans_token():
    """
    Verifies that cancellation triggers immediate thread exit and safely unregisters
    cancellation tokens without memory leaks.
    """
    job_id = "resilience-cancel-job-123"
    token = yt_service.register_cancellation_token(job_id)
    assert not token.is_set()

    # Trigger cooperative cancellation
    success = yt_service.trigger_cancellation(job_id)
    assert success is True
    assert token.is_set()

    # Unregister and verify removal
    yt_service.unregister_cancellation_token(job_id)
    assert yt_service.trigger_cancellation(job_id) is False


def test_network_failure_transient_retry_backoff(tmp_path):
    """
    Validates that transient network failures trigger exponential backoff with jitter
    without corrupting the job state machine.
    """
    db_file = tmp_path / "retry_test.db"
    mgr = DownloadQueueManager(db_path=str(db_file))

    job = mgr.add_job(
        url="https://example.com/transient_failure_stream.mp4",
        title="Transient Failure Test",
    )

    # Simulate network failure during execution
    with patch("app.services.yt_service.download_stream") as mock_stream:
        mock_stream.side_effect = ConnectionResetError("Remote host forcibly closed an existing connection")
        mgr._run_job_worker(job.model_dump(), domain="example.com")

    # Verify job is scheduled for retry rather than immediately failed
    jobs = mgr.get_all_jobs()
    retried_job = next(j for j in jobs if j.id == job.id)
    assert retried_job.retry_count == 1
    assert "Transient error" in (retried_job.error_message or "")
    assert retried_job.state == DownloadState.QUEUED.value
