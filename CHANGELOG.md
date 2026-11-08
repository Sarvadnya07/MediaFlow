# Changelog

All notable changes to MediaDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-rc.1] - 2026-11-08

### Added
- **Native Desktop Shell & Architecture**: Production Tauri 2 + Rust supervisor running an isolated Python yt-dlp worker exclusively over stdio JSON Lines (`stdin`/`stdout`).
- **Universal Provider Ecosystem**: Extensible registry supporting universal yt-dlp fallback and direct HTTP/HTTPS web media parsing with automatic range request detection.
- **Intelligent Download Engine**: Priority scheduling, per-provider domain concurrency throttling, exponential backoff with jitter retry, atomic `.part` promotions, and pause/resume.
- **Local Media Library & Storage**: SQLite-backed local catalog, file favorites, safe rename/deletion within contained boundaries, and real disk usage metrics via `shutil.disk_usage`.
- **Media Intelligence & Subtitles**: Heuristic title fluff stripping, timestamped chapter extraction, category classification, transparent AI disclosure flags, and multi-language subtitle parsing.
- **Desktop Automation**: System clipboard URL monitoring, drag-and-drop validation for media/subtitles, and configurable night-time download execution windows.
- **Auto-Updates & Release Channels**: Stable (default), Beta, and Development release channels, SHA256 manifest verification, and zero-downtime SQLite online backup before schema changes.
- **Observability & Diagnostics**: Structured JSON logging, automated credential token redaction (`[REDACTED]`), 5MB rotating file handler, and comprehensive system diagnostics telemetry.
- **Security & Hardening**: Strict RFC 1918 / loopback IP blocking, DNS rebinding guards, canonical directory traversal containment, zero DRM circumvention, and no cookie harvesting.

### Verified
- Automated test matrix: 58/58 passing tests across Python, Rust, and TypeScript.
- Release binary builds on Windows x86_64 (`mediadock.exe` 9.7MB, standalone sidecar 30.0MB).
