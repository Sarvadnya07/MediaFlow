import io
import json
import pytest
from unittest.mock import patch, MagicMock
from app.engine.sidecar import SidecarRunner
from app.engine.protocol import MediaAnalysisResult, MediaFormatInfo


@pytest.fixture
def mock_io():
    stdin = io.StringIO()
    stdout = io.StringIO()
    runner = SidecarRunner(stdin=stdin, stdout=stdout)
    return runner, stdin, stdout


def test_sidecar_initialize(mock_io):
    runner, stdin, stdout = mock_io
    runner.handle_raw_message(json.dumps({"id": "req-1", "action": "initialize"}))
    output = json.loads(stdout.getvalue().strip())
    assert output["id"] == "req-1"
    assert output["status"] == "success"
    assert output["data"]["status"] == "ready"


def test_sidecar_health_check(mock_io):
    runner, stdin, stdout = mock_io
    runner.handle_raw_message(json.dumps({"id": "req-2", "action": "health_check"}))
    output = json.loads(stdout.getvalue().strip())
    assert output["id"] == "req-2"
    assert output["status"] == "success"
    assert "dependencies" in output["data"]


def test_sidecar_get_capabilities(mock_io):
    runner, stdin, stdout = mock_io
    runner.handle_raw_message(json.dumps({"id": "req-3", "action": "get_capabilities"}))
    output = json.loads(stdout.getvalue().strip())
    assert output["id"] == "req-3"
    assert "supported_actions" in output["data"]
    assert "download" in output["data"]["supported_actions"]


def test_sidecar_invalid_json(mock_io):
    runner, stdin, stdout = mock_io
    runner.handle_raw_message("not a valid json string{{{")
    output = json.loads(stdout.getvalue().strip())
    assert output["status"] == "error"
    assert output["error"]["code"] == "INVALID_JSON"


def test_sidecar_validation_error(mock_io):
    runner, stdin, stdout = mock_io
    runner.handle_raw_message(json.dumps({"id": "req-bad", "action": "nonexistent_action"}))
    output = json.loads(stdout.getvalue().strip())
    assert output["status"] == "error"
    assert output["error"]["code"] == "VALIDATION_ERROR"


@patch("app.services.yt_service.analyze_url")
def test_sidecar_analyze(mock_analyze, mock_io):
    runner, stdin, stdout = mock_io
    mock_analyze.return_value = MediaAnalysisResult(
        url="https://example.com/video",
        extractor="generic",
        id="v123",
        title="Test Title",
        duration=120,
        formats=[
            MediaFormatInfo(format_id="18", ext="mp4", resolution="640x360", has_video=True, has_audio=True)
        ],
        subtitles=["en"],
        automatic_captions=[]
    )

    req = {"id": "req-analyze", "action": "analyze", "payload": {"url": "https://example.com/video"}}
    runner.handle_raw_message(json.dumps(req))

    output = json.loads(stdout.getvalue().strip())
    assert output["id"] == "req-analyze"
    assert output["status"] == "success"
    assert output["data"]["title"] == "Test Title"
    assert len(output["data"]["formats"]) == 1


def test_sidecar_cancel(mock_io):
    runner, stdin, stdout = mock_io
    req = {"id": "req-cancel", "action": "cancel", "payload": {"job_id": "job-999"}}
    runner.handle_raw_message(json.dumps(req))
    output = json.loads(stdout.getvalue().strip())
    assert output["id"] == "req-cancel"
    assert output["status"] == "success"
    assert output["data"]["job_id"] == "job-999"


def test_sidecar_providers_list(mock_io):
    runner, stdin, stdout = mock_io
    req = {"id": "req-prov", "action": "providers_list"}
    runner.handle_raw_message(json.dumps(req))
    output = json.loads(stdout.getvalue().strip())
    assert output["id"] == "req-prov"
    assert output["status"] == "success"
    assert "providers" in output["data"]
    assert len(output["data"]["providers"]) >= 2


def test_sidecar_intelligence_enrich(mock_io):
    runner, stdin, stdout = mock_io
    req = {
        "id": "req-enrich",
        "action": "intelligence_enrich",
        "payload": {"title": "Learn Rust in 2026 [4K 60FPS Tutorial]", "description": "00:00 Intro\n01:30 Setup"},
    }
    runner.handle_raw_message(json.dumps(req))
    output = json.loads(stdout.getvalue().strip())
    assert output["id"] == "req-enrich"
    assert output["status"] == "success"
    assert output["data"]["cleaned_title"] == "Learn Rust in 2026"
    assert len(output["data"]["chapters"]) == 2

