import os
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import yt_dlp

from ..config import settings
from ..logging_config import logger
from .ffmpeg_service import get_ffmpeg_capabilities, resolve_ffprobe_path


class DiagnosticsService:
    @staticmethod
    def get_system_diagnostics(recent_errors_limit: int = 20) -> Dict[str, Any]:
        """
        Aggregate comprehensive diagnostic telemetry across application layers:
        versions, environment, database status, binaries, and recent error logs.
        """
        # 1. System and Platform
        sys_info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
        }

        # 2. Dependency Versions
        dep_info = {
            "app_version": "1.0.0",
            "yt_dlp_version": yt_dlp.version.__version__,
            "sqlite_version": sqlite3.sqlite_version,
        }

        # 3. FFmpeg and FFprobe Diagnostics
        ffmpeg_caps = get_ffmpeg_capabilities()
        ffprobe_available = False
        ffprobe_path = None
        try:
            ffprobe_path = resolve_ffprobe_path()
            ffprobe_available = True
        except Exception:
            ffprobe_available = False

        binary_info = {
            "ffmpeg": {
                "available": ffmpeg_caps.get("available", False),
                "version": ffmpeg_caps.get("version"),
                "audio_encoders": ffmpeg_caps.get("audio_encoders", []),
                "video_encoders": ffmpeg_caps.get("video_encoders", []),
                "error": ffmpeg_caps.get("error"),
            },
            "ffprobe": {
                "available": ffprobe_available,
                "path": ffprobe_path,
            },
        }

        # 4. Database Status and Queue Metrics
        db_path = Path("downloads.db")
        db_status = {
            "connected": False,
            "path": str(db_path.resolve()) if db_path.exists() else "in-memory / uninitialized",
            "size_bytes": db_path.stat().st_size if db_path.exists() else 0,
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "pending_jobs": 0,
        }

        try:
            if db_path.exists():
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='download_queue'")
                    if cursor.fetchone()[0] > 0:
                        db_status["connected"] = True
                        cursor.execute("SELECT count(*) FROM download_queue")
                        db_status["total_jobs"] = cursor.fetchone()[0]
                        cursor.execute("SELECT count(*) FROM download_queue WHERE status='completed'")
                        db_status["completed_jobs"] = cursor.fetchone()[0]
                        cursor.execute("SELECT count(*) FROM download_queue WHERE status='failed'")
                        db_status["failed_jobs"] = cursor.fetchone()[0]
                        cursor.execute("SELECT count(*) FROM download_queue WHERE status IN ('queued', 'downloading')")
                        db_status["pending_jobs"] = cursor.fetchone()[0]
            else:
                db_status["connected"] = True  # Can connect or create on demand
        except Exception as e:
            db_status["error"] = str(e)

        # 5. Recent Error Logs Retrieval
        recent_errors = DiagnosticsService._read_recent_error_logs(recent_errors_limit)

        return {
            "system": sys_info,
            "dependencies": dep_info,
            "binaries": binary_info,
            "database": db_status,
            "recent_errors": recent_errors,
        }

    @staticmethod
    def _read_recent_error_logs(limit: int = 20, custom_log_file: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Read the tail of the rotating log file and filter for WARNING / ERROR / CRITICAL."""
        if custom_log_file:
            log_file = custom_log_file
        else:
            log_dir = Path(settings.DOWNLOADS_DIR).parent / "logs"
            log_file = log_dir / "mediadock.log"

        if not log_file.exists():
            return []

        errors = []
        try:
            import json
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        record = json.loads(line_str)
                        sev = record.get("severity", "").upper()
                        if sev in ("ERROR", "CRITICAL", "WARNING"):
                            errors.append(record)
                            if len(errors) >= limit:
                                break
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Failed to read diagnostics log tail: {e}")

        return errors
