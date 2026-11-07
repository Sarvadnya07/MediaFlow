# MediaDock — Build Status & Task Tracker

## 1. Project Overview
MediaDock is a modern, cross-platform desktop media management and download suite upgrading the existing `yt_dlp_backend` engine into a Tauri 2 + Rust desktop architecture with a React + TypeScript frontend and a Python + yt-dlp IPC sidecar.

## 2. Current Implementation State
- **Phase 1: Deep Repository Audit:** COMPLETED (`ec7b3e6`)
- **Phase 2: Backend Refactoring & Sidecar Protocol:** **COMPLETED & VERIFIED**.
  - **Working Branch:** `feat/phase-2-backend-refactor`
  - **Security Fixes Applied:**
    - Path traversal in `/v1/files/{filename}` patched with `ensure_within_directory`.
    - Global exception handler sanitized; stack traces isolated to server log.
    - SSRF protection implemented via `validate_and_sanitize_url`.
    - Obsolete scripts (`fix.py`, `app/routes/a.py`) removed.
  - **Media Engine Decoupling:**
    - `app/services/yt_service.py` refactored into pure functions: `analyze_url`, `download_stream`, cancellation token registry.
    - `app/services/ffmpeg_service.py` refactored: dynamic binary discovery (`resolve_ffmpeg_path`), safe subprocess argument lists, error handling.
    - SQLite persistence upgraded with WAL mode and foreign-key pragma hooks in `app/database.py`.
  - **Sidecar JSONL IPC:**
    - Protocol defined in `app/engine/protocol.py`.
    - Runner implemented in `app/engine/sidecar.py` supporting `initialize`, `health_check`, `analyze`, `get_formats`, `download`, `cancel`, `convert`, `get_capabilities`, and `shutdown`.
    - Tested using `pytest`: **16/16 tests passing**.

## 3. Mandatory Governance Artifacts
- [x] `BUILD_STATUS.md` — Active tracker
- [x] `docs/PROJECT_AUDIT.md` — Historical audit verification and security assessment
- [x] `docs/ARCHITECTURE.md` — System architecture and IPC contract design
- [x] `docs/DECISIONS.md` — Architectural Decision Records (ADR-001 through ADR-006)
- [x] `docs/MIGRATION_PLAN.md` — Phased migration strategy
- [x] `docs/KNOWN_LIMITATIONS.md` — Platform, DRM, and temporary disk constraints
- [x] `docs/TEST_REPORT.md` — Automated test report (16 passing tests)

## 4. Next Phase
- **Phase 3 / Next Task:** **Tauri 2 + Rust Desktop Integration & Frontend Setup**
  - Scaffold `src-tauri` with Tauri 2 and Rust dependencies.
  - Implement Rust sidecar process supervisor and Tokio-based JSONL IPC communication channel.
  - Scaffold React + TypeScript + Vite frontend with Tailwind CSS and shadcn/ui.
