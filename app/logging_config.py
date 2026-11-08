import json
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional
from .config import settings

# Sensitive token / secret redaction patterns
REDACT_PATTERNS = [
    re.compile(r'((?:key|token|auth|password|secret|credential|signature|sig)=)([^&\s]+)', re.IGNORECASE),
    re.compile(r'(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*', re.IGNORECASE),
]


def redact_sensitive_data(text: str) -> str:
    """Safely redact credentials, API tokens, and authorization query params."""
    if not isinstance(text, str):
        return text
    redacted = text
    for pattern in REDACT_PATTERNS:
        redacted = pattern.sub(r'\1[REDACTED]', redacted)
    return redacted


class StructuredJsonFormatter(logging.Formatter):
    """
    Production-grade JSON logger that captures component, operation_id, job_id,
    and automatically redacts credentials.
    """
    def format(self, record: logging.LogRecord) -> str:
        msg = redact_sensitive_data(record.getMessage())
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "severity": record.levelname,
            "component": getattr(record, "component", record.name),
            "message": msg,
            "file": record.filename,
            "line": record.lineno,
        }

        # Optional correlation metadata
        if hasattr(record, "job_id"):
            log_entry["job_id"] = record.job_id
        if hasattr(record, "operation_id"):
            log_entry["operation_id"] = record.operation_id
        if hasattr(record, "error_code"):
            log_entry["error_code"] = record.error_code

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(log_dir: Optional[str] = None):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = StructuredJsonFormatter()

    # 1. Console Handler routed strictly to sys.stderr so stdio stdout is isolated for IPC
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler with size caps (5MB per file, 3 backups = 15MB max)
    target_dir = Path(log_dir or Path(settings.DOWNLOADS_DIR).parent / "logs")
    target_dir.mkdir(parents=True, exist_ok=True)
    log_file = target_dir / "mediadock.log"

    rotating_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    rotating_handler.setFormatter(formatter)
    root_logger.addHandler(rotating_handler)

    # Suppress verbose noisy third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger("mediadock")
    logger.info("Structured JSON Logging initialized with log rotation and redaction")
    return logger


logger = setup_logging()
