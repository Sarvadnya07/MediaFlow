import pytest
from unittest.mock import patch, MagicMock
from app.services import yt_service
from app.services.yt_service import DownloadCancelledError
from app.engine.protocol import MediaAnalysisResult


@patch("yt_dlp.YoutubeDL")
def test_analyze_url_success(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    mock_ydl.extract_info.return_value = {
        "id": "abc1234",
        "extractor": "youtube",
        "title": "Rick Astley",
        "description": "Music Video",
        "duration": 213,
        "uploader": "Official Rick Astley",
        "thumbnail": "https://img.youtube.com/vi/abc1234/0.jpg",
        "formats": [
            {
                "format_id": "137",
                "ext": "mp4",
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "vcodec": "avc1",
                "acodec": "none",
                "format_note": "1080p",
            },
            {
                "format_id": "140",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "format_note": "medium",
            }
        ],
        "subtitles": {"en": [{"ext": "vtt"}]},
        "automatic_captions": {"es": [{"ext": "vtt"}]}
    }

    res = yt_service.analyze_url("https://example.com/watch?v=abc1234")
    assert isinstance(res, MediaAnalysisResult)
    assert res.title == "Rick Astley"
    assert len(res.formats) == 2
    assert res.formats[0].has_video is True
    assert res.formats[0].has_audio is False
    assert res.formats[1].has_audio is True
    assert "en" in res.subtitles
    assert "es" in res.automatic_captions


def test_cancellation_token_registration_and_trigger():
    job_id = "test-job-cancel-1"
    token = yt_service.register_cancellation_token(job_id)
    assert not token.is_set()

    assert yt_service.trigger_cancellation(job_id) is True
    assert token.is_set()

    yt_service.unregister_cancellation_token(job_id)
    assert yt_service.trigger_cancellation(job_id) is False
