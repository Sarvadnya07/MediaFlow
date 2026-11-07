# MediaDock — Architectural Decision Records (ADR)

## ADR-001: Sidecar JSON Lines IPC vs Local HTTP Server
- **Date:** 2026-11-08
- **Status:** Accepted
- **Context:** MediaDock requires communication between Tauri 2 (Rust) desktop host and Python media engine (`yt-dlp`).
- **Options Considered:**
  1. *Local HTTP/FastAPI Server:* Spawn Uvicorn on localhost with an assigned port.
  2. *Structured JSON Lines over stdio IPC:* Tauri child process with piped stdin/stdout.
- **Decision:** Structured JSON Lines over stdio.
- **Rationale:**
  - Running a local HTTP server introduces attack surface (CORS, loopback binding vulnerabilities, firewall warnings for users, port collisions).
  - Stdio pipes are private to the parent process, robust, high throughput, and avoid network socket overhead.
  - Lifecycle coupling is automatic: if Tauri closes, the pipe closes and the child process exits immediately without orphan zombie servers.

## ADR-002: In-Process Queue Orchestration vs Celery/Redis for Desktop
- **Date:** 2026-11-08
- **Status:** Accepted
- **Context:** The original backend used Celery + Redis for asynchronous background tasks.
- **Decision:** For desktop distribution, replace Redis/Celery background dependencies with an in-process Rust task queue worker communicating directly with the Python sidecar.
- **Rationale:**
  - Requiring desktop users to install or bundle Redis is impractical and consumes excessive system resources.
  - Rust's Tokio runtime provides superior concurrency, lifecycle control, and real-time event streaming directly to the Webview.
  - The original Celery worker scripts remain intact in `app/worker` for server deployments, but desktop runtime operates independently.

## ADR-003: Preservation of SQLite and Schema Models
- **Date:** 2026-11-08
- **Status:** Accepted
- **Context:** MediaDock tracks download history, preferences, and queue items.
- **Decision:** Retain SQLite as the primary persistent storage layer, maintaining compatibility with existing Alembic migrations and SQLAlchemy models.
- **Rationale:**
  - SQLite is single-file, zero-dependency, and works across Windows, macOS, and Linux out of the box.
  - Existing models (`Download`, `User`, etc.) can be reused with zero migration friction.

## ADR-004: FFmpeg Discovery and Resolution Strategy
- **Date:** 2026-11-08
- **Status:** Accepted
- **Context:** yt-dlp relies heavily on FFmpeg for audio/video merging, transcoding, and subtitle extraction.
- **Decision:** MediaDock implements a hierarchical FFmpeg resolver:
  1. User-configured custom binary path in app settings.
  2. App-bundled binary directory (for packaged portable distributions).
  3. System PATH fallback.
- **Rationale:** Guarantees functionality on fresh machines without pre-installed system packages while supporting power-user customized FFmpeg builds.

## ADR-005: Retention and Isolation of Headless Server Code
- **Date:** 2026-11-08
- **Status:** Accepted
- **Context:** The repository contains a complete FastAPI / Celery / Docker deployment.
- **Decision:** Do not delete or overwrite the FastAPI and Celery code. Keep it isolated and functional for headless/server deployment while building the Tauri desktop engine in parallel.
- **Rationale:** Prevents regression for users running `docker-compose up` while enabling the Tauri desktop application to use the same underlying `yt-dlp` services.

## ADR-006: Hardening Security & Sanitizing Input/Output
- **Date:** 2026-11-08
- **Status:** Accepted
- **Context:** Audit revealed path traversal in `/v1/files/{filename}`, secret leakage via tracked `.env`, and unhandled exception details leaking system paths.
- **Decision:** Remove `.env` from Git tracking, provide `.env.example`, enforce strict path containment checks on all file endpoints, and sanitize exception handlers.
- **Rationale:** Protects user privacy and host system integrity across both server and desktop operating environments.
