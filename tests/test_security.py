import pytest
from app.security import validate_and_sanitize_url, sanitize_filename, ensure_within_directory, SecurityError
from pathlib import Path


def test_valid_urls():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert validate_and_sanitize_url(url) == url

    url2 = "http://example.com/media/audio.mp3"
    assert validate_and_sanitize_url(url2) == url2


def test_reject_unsupported_schemes():
    with pytest.raises(SecurityError, match="Unsupported scheme"):
        validate_and_sanitize_url("file:///etc/passwd")

    with pytest.raises(SecurityError, match="Unsupported scheme"):
        validate_and_sanitize_url("ftp://server/file.mp4")

    with pytest.raises(SecurityError, match="Unsupported scheme"):
        validate_and_sanitize_url("gopher://server/test")


def test_reject_embedded_credentials():
    with pytest.raises(SecurityError, match="Embedded credentials"):
        validate_and_sanitize_url("https://admin:password@example.com/video")


def test_reject_loopback_and_private_ips():
    with pytest.raises(SecurityError, match="Access to loopback target"):
        validate_and_sanitize_url("http://localhost:8000/media")

    with pytest.raises(SecurityError, match="Access to loopback target"):
        validate_and_sanitize_url("http://127.0.0.1:8000/media")

    with pytest.raises(SecurityError, match="Restricted private/local IP"):
        validate_and_sanitize_url("http://192.168.1.100/video.mp4")

    with pytest.raises(SecurityError, match="Restricted private/local IP"):
        validate_and_sanitize_url("http://10.0.0.1/video.mp4")


def test_sanitize_filename():
    assert sanitize_filename("safe_video.mp4") == "safe_video.mp4"
    assert sanitize_filename("../../etc/passwd") == "etc_passwd"
    assert sanitize_filename('video:with"invalid/chars*') == "video_with_invalid_chars"
    assert sanitize_filename("   spaced name . ") == "spaced name"
    assert sanitize_filename("") == "unnamed_media"


def test_directory_containment():
    base_dir = Path("/mock/downloads")
    
    # Safe path inside base_dir
    safe = base_dir / "subdir" / "video.mp4"
    assert ensure_within_directory(safe, base_dir) == safe.resolve()

    # Path traversal outside base_dir
    unsafe = base_dir / ".." / "system32" / "cmd.exe"
    with pytest.raises(SecurityError, match="Path traversal detected"):
        ensure_within_directory(unsafe, base_dir)
