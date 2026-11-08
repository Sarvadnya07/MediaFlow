"""
MediaDock Desktop Automation Engine & Scheduling Controller.
Provides:
- Time-window based execution scheduler (start/pause at specific hours).
- Automation preferences model (opt-in clipboard monitoring, notification preferences, concurrency).
- Drag-and-drop file & URL path validator.
- Persistence across application restarts.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.logging_config import logger
from app.security import validate_and_sanitize_url, ensure_within_directory, SecurityError


class NotificationPreferences(BaseModel):
    on_download_complete: bool = True
    on_download_failed: bool = True
    on_conversion_complete: bool = True
    on_dependency_missing: bool = True


class ExecutionWindow(BaseModel):
    enabled: bool = False
    start_hour: int = 0  # 0-23
    start_minute: int = 0
    end_hour: int = 23
    end_minute: int = 59


class AutomationSettings(BaseModel):
    clipboard_monitoring_enabled: bool = False
    auto_import_prompt: bool = True
    auto_download_without_confirm: bool = False  # Hard enforced to False
    execution_window: ExecutionWindow = Field(default_factory=ExecutionWindow)
    notifications: NotificationPreferences = Field(default_factory=NotificationPreferences)
    bandwidth_limit_kbps: Optional[int] = None
    global_shortcuts_enabled: bool = True


class AutomationEngine:
    def __init__(self, config_path: Optional[str] = None):
        self.config_file = Path(config_path or Path(settings.DOWNLOADS_DIR).parent / "automation_config.json")
        self.settings = self._load_settings()

    def _load_settings(self) -> AutomationSettings:
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                return AutomationSettings(**data)
            except Exception as e:
                logger.warning(f"Failed to load automation config, falling back to defaults: {e}")
        return AutomationSettings()

    def save_settings(self, new_settings: Dict[str, Any]) -> AutomationSettings:
        # Prevent automatic downloading without explicit user confirmation
        if "auto_download_without_confirm" in new_settings:
            new_settings["auto_download_without_confirm"] = False

        self.settings = AutomationSettings(**new_settings)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(self.settings.model_dump(), indent=2), encoding="utf-8")
        return self.settings

    def is_within_execution_window(self, dt: Optional[datetime] = None) -> bool:
        """Evaluate whether current local time is within the configured download window."""
        if not self.settings.execution_window.enabled:
            return True

        now = dt or datetime.now()
        current_minute = now.hour * 60 + now.minute
        start_min = self.settings.execution_window.start_hour * 60 + self.settings.execution_window.start_minute
        end_min = self.settings.execution_window.end_hour * 60 + self.settings.execution_window.end_minute

        if start_min <= end_min:
            return start_min <= current_minute <= end_min
        else:
            # Spans overnight / midnight
            return current_minute >= start_min or current_minute <= end_min

    def validate_dropped_item(self, raw_input: str) -> Dict[str, Any]:
        """
        Validate drag-and-dropped item.
        Determines whether it is a supported web URL or a local media / subtitle file.
        """
        cleaned = raw_input.strip().strip("'\"")

        # 1. Check if it is a valid web URL
        if cleaned.startswith(("http://", "https://")):
            try:
                safe_url = validate_and_sanitize_url(cleaned)
                return {
                    "type": "url",
                    "valid": True,
                    "target": safe_url,
                    "action": "prompt_import",
                }
            except SecurityError as se:
                return {
                    "type": "url",
                    "valid": False,
                    "error": str(se),
                }

        # 2. Check if it is a local filesystem path
        path_obj = Path(cleaned).resolve()
        if path_obj.exists() and path_obj.is_file():
            ext = path_obj.suffix.lower()
            if ext in {".srt", ".vtt", ".ass", ".sub"}:
                return {
                    "type": "subtitle",
                    "valid": True,
                    "target": str(path_obj),
                    "action": "import_subtitle",
                }
            elif ext in {".mp4", ".mkv", ".webm", ".avi", ".mov", ".mp3", ".m4a", ".flac", ".wav", ".opus"}:
                return {
                    "type": "media",
                    "valid": True,
                    "target": str(path_obj),
                    "action": "import_library",
                }
            else:
                return {
                    "type": "file",
                    "valid": False,
                    "error": f"Unsupported file extension '{ext}' for media or subtitle import.",
                }

        return {
            "type": "unknown",
            "valid": False,
            "error": "Dropped item is neither an accessible local file nor a valid HTTP/S URL.",
        }


automation_engine = AutomationEngine()
