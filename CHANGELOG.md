# Changelog

All notable changes to **MediaFlow** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-rc.1] - 2026-11-08

### Added
- **Native Desktop Topology**: Production Tauri 2 + Rust supervisor executing an isolated Python yt-dlp media engine via standard I/O (`stdin`/`stdout` JSON Lines protocol).
- **Headless & Distributed Backend**: FastAPI REST and WebSocket endpoints with Celery worker pipeline backed by Redis task broker and PostgreSQL/SQLite persistence.
- **Universal Provider Architecture**: Extensible provider registry with yt-dlp universal extractor fallback and direct HTTP/HTTPS web media parsing with automatic byte-range header detection.
- **Resilient Download Pipeline**: Multi-priority download queue, per-domain concurrency rate limiting, exponential backoff with randomized jitter, atomic `.part` promotions, and safe pause/resume lifecycle.
- **Local Media Management**: SQLite WAL-backed metadata catalog, favorites tagging, safe containment-checked renaming/deletion, and real-time disk quota monitoring via `shutil.disk_usage`.
- **Media Post-Processing & Intelligence**: Heuristic video title fluff cleanup, chapter extraction, category detection, subtitle stream parsing, and FFmpeg transcode/audio extraction presets.
- **Desktop Automation**: System clipboard media URL watcher, drag-and-drop validation for media streams, and configurable nighttime scheduled download windows.
- **Defense-in-Depth Security**: RFC 1918 private IP blocking, DNS rebinding guards, canonical path traversal protections, CSP policies, zero DRM circumvention, and zero cookie harvesting.
- **Repository Quality & Hygiene**: Modularized React UI components, strict single-direction dependency graph, comprehensive `.env.example`, cross-platform `.gitattributes`, and strict `.gitignore` rules.

### Changed
- Refactored frontend navigation into isolated, domain-focused tab views (`AnalysisView`, `QueueView`, `LibraryView`, `ConverterView`, `AutomationView`, `DiagnosticsView`, `SettingsView`).
- Standardized all application timestamps to timezone-aware UTC (`datetime.now(timezone.utc)`).
- Upgraded test harness with `@pytest.mark.network` annotations for rapid, deterministic offline test runs.

### Verified
- Automated test matrix: 79 passing tests across Python (72), Vitest (4), and Cargo (3).
- Clean cross-platform artifact builds on Windows x86_64.
