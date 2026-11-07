import os
import pytest
from pathlib import Path
from app.services.ffmpeg_service import verify_media_file, FFmpegResolutionError
from app.services.yt_service import download_stream


def test_verify_media_file_nonexistent():
    with pytest.raises(FileNotFoundError):
        verify_media_file("nonexistent_path_file.mp4")


def test_verify_media_file_empty(tmp_path):
    empty_file = tmp_path / "empty.mp4"
    empty_file.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        verify_media_file(str(empty_file))


def test_download_stream_and_verify_real_authorized_media(tmp_path):
    """
    Acceptance test demonstrating a complete real media download,
    real-time progress hooks, non-zero file existence, and container verification.
    Uses a minimal authorized test stream.
    """
    # 1-second sample video URL from public archive
    test_url = "https://raw.githubusercontent.com/bower-media-samples/big-buck-bunny-1080p-60fps-30s/master/video.mp4"

    progress_events = []

    def on_progress(p):
        progress_events.append(p)

    job_id = "test-real-download-1"
    res = download_stream(
        url=test_url,
        output_dir=tmp_path,
        job_id=job_id,
        progress_callback=on_progress,
        allow_private=True,
    )

    assert res["status"] == "completed"
    assert res["job_id"] == job_id
    assert os.path.exists(res["filepath"])
    assert res["filesize"] > 0
    assert len(progress_events) > 0

    # FFprobe verification
    verified = verify_media_file(res["filepath"])
    assert verified["valid"] is True
    assert verified["filesize"] > 0
    assert verified["has_video"] is True
