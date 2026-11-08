"""
MediaDock Desktop Automation & Productivity Tests.
Verifies execution window scheduling, opt-in automation preferences,
drag-and-drop file and URL validation, and persistent settings.
"""
from datetime import datetime
import pytest
from app.services.automation_service import AutomationEngine


def test_automation_settings_load_and_save(tmp_path):
    cfg_file = tmp_path / "automation_test.json"
    engine = AutomationEngine(config_path=str(cfg_file))

    # Defaults
    assert engine.settings.clipboard_monitoring_enabled is False
    assert engine.settings.auto_download_without_confirm is False

    # Save update
    updated = engine.save_settings({
        "clipboard_monitoring_enabled": True,
        "auto_import_prompt": True,
        "auto_download_without_confirm": True,  # Must be enforced to False
        "execution_window": {
            "enabled": True,
            "start_hour": 2,
            "start_minute": 0,
            "end_hour": 6,
            "end_minute": 0,
        },
        "notifications": {
            "on_download_complete": True,
            "on_download_failed": True,
        }
    })

    assert updated.clipboard_monitoring_enabled is True
    assert updated.auto_download_without_confirm is False  # Enforced False
    assert updated.execution_window.enabled is True

    # Confirm reload
    reload_engine = AutomationEngine(config_path=str(cfg_file))
    assert reload_engine.settings.clipboard_monitoring_enabled is True
    assert reload_engine.settings.execution_window.start_hour == 2


def test_execution_window_evaluation(tmp_path):
    cfg_file = tmp_path / "window_test.json"
    engine = AutomationEngine(config_path=str(cfg_file))

    engine.save_settings({
        "execution_window": {
            "enabled": True,
            "start_hour": 1,
            "start_minute": 0,
            "end_hour": 5,
            "end_minute": 0,
        }
    })

    # Time at 03:00 -> True
    t_inside = datetime(2026, 11, 8, 3, 0)
    assert engine.is_within_execution_window(t_inside) is True

    # Time at 08:00 -> False
    t_outside = datetime(2026, 11, 8, 8, 0)
    assert engine.is_within_execution_window(t_outside) is False


def test_drag_and_drop_validation(tmp_path):
    engine = AutomationEngine(config_path=str(tmp_path / "drop_test.json"))

    # Valid web URL
    url_res = engine.validate_dropped_item("https://example.com/stream.mp4")
    assert url_res["valid"] is True
    assert url_res["type"] == "url"

    # Local media file
    media_file = tmp_path / "movie.mp4"
    media_file.write_bytes(b"sample video bytes")
    media_res = engine.validate_dropped_item(str(media_file))
    assert media_res["valid"] is True
    assert media_res["type"] == "media"

    # Local subtitle file
    sub_file = tmp_path / "subtitles.srt"
    sub_file.write_text("1\n00:00:01,000 --> 00:00:03,000\nHello")
    sub_res = engine.validate_dropped_item(str(sub_file))
    assert sub_res["valid"] is True
    assert sub_res["type"] == "subtitle"

    # Invalid / non-existent target
    invalid_res = engine.validate_dropped_item("non_existent_file_or_protocol.xyz")
    assert invalid_res["valid"] is False
