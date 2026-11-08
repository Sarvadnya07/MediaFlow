import json
import logging
import tempfile
from pathlib import Path
from app.logging_config import StructuredJsonFormatter, redact_sensitive_data
from app.services.diagnostics_service import DiagnosticsService


def test_redact_sensitive_data():
    raw = "Request failed: https://api.example.com/download?key=SECRET123&other=456&token=SUPER_SECRET_TOKEN"
    redacted = redact_sensitive_data(raw)
    assert "SECRET123" not in redacted
    assert "SUPER_SECRET_TOKEN" not in redacted
    assert "key=[REDACTED]" in redacted
    assert "token=[REDACTED]" in redacted

    bearer_raw = "Authorization: Bearer abcd1234efgh5678"
    bearer_redacted = redact_sensitive_data(bearer_raw)
    assert "abcd1234efgh5678" not in bearer_redacted
    assert "[REDACTED]" in bearer_redacted


def test_structured_json_formatter():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=42,
        msg="Authentication failed for token=TOP_SECRET",
        args=(),
        exc_info=None,
    )
    record.job_id = "job-999"
    record.operation_id = "op-888"
    record.error_code = "AUTH_FAIL"

    formatted_str = formatter.format(record)
    parsed = json.loads(formatted_str)

    assert parsed["severity"] == "ERROR"
    assert parsed["job_id"] == "job-999"
    assert parsed["operation_id"] == "op-888"
    assert parsed["error_code"] == "AUTH_FAIL"
    assert "TOP_SECRET" not in parsed["message"]
    assert "[REDACTED]" in parsed["message"]


def test_diagnostics_service_payload_structure():
    diag = DiagnosticsService.get_system_diagnostics(recent_errors_limit=5)
    assert "system" in diag
    assert "dependencies" in diag
    assert "binaries" in diag
    assert "database" in diag
    assert "recent_errors" in diag

    # Verify system details
    assert "platform" in diag["system"]
    assert "python_version" in diag["system"]

    # Verify dependency versions
    assert diag["dependencies"]["app_version"] == "1.0.0"
    assert "yt_dlp_version" in diag["dependencies"]
    assert "sqlite_version" in diag["dependencies"]

    # Verify binary capabilities
    assert "ffmpeg" in diag["binaries"]
    assert "ffprobe" in diag["binaries"]
    assert "available" in diag["binaries"]["ffmpeg"]


def test_diagnostics_service_log_reading(monkeypatch, tmp_path):
    mock_log = tmp_path / "mediadock.log"
    entry_1 = json.dumps({"timestamp": "2026-11-08T12:00:00", "severity": "INFO", "message": "Normal startup"})
    entry_2 = json.dumps({"timestamp": "2026-11-08T12:01:00", "severity": "WARNING", "message": "Low memory"})
    entry_3 = json.dumps({"timestamp": "2026-11-08T12:02:00", "severity": "ERROR", "message": "Download failed"})

    mock_log.write_text(f"{entry_1}\n{entry_2}\n{entry_3}\n", encoding="utf-8")

    errors = DiagnosticsService._read_recent_error_logs(limit=10, custom_log_file=mock_log)
    assert len(errors) == 2
    assert errors[0]["severity"] == "ERROR"
    assert errors[1]["severity"] == "WARNING"
