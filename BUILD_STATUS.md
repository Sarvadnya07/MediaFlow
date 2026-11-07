# MediaDock — Build Status & Task Tracker

## 1. Project Overview
MediaDock is a modern, cross-platform desktop media management and download suite upgrading the existing `yt_dlp_backend` engine into a Tauri 2 + Rust desktop architecture with a React + TypeScript frontend and a Python + yt-dlp IPC sidecar.

## 2. Current Implementation State
- **Phase:** Phase 1 (Deep Repository Audit) — **COMPLETED & VERIFIED**.
- **Working Branch Checkpoint:** `chore/phase-1-deep-audit`
- **Security & Hygiene Checkpoint:**
  - Tracked `.env` file untracked from Git index (`git rm --cached .env`).
  - `.env.example` created with template variables.
  - `.gitignore` hardened against secrets, virtual environments, sqlite files, logs, and binaries.
  - Tracked `__pycache__`, `.db`, and video files removed from Git index.
- **Component Evaluation:**
  - `app/services/yt_service.py`: Identified for refactoring into pure engine functions.
  - `app/services/ffmpeg_service.py`: Identified for multi-source binary resolution and robust subprocess execution.
  - `app/routes/files.py`: Path traversal vulnerability identified and queued for immediate patching.
  - `app/main.py`: Internal exception trace leakage identified and queued for remediation.
  - Celery / Redis: Preserved for headless server deployments; queued for replacement by in-process Tokio queue for Tauri desktop.

## 3. Mandatory Governance Artifacts
- [x] `BUILD_STATUS.md` — Active tracker
- [x] `docs/PROJECT_AUDIT.md` — Complete verification of historical claims, security audit, and component assessment
- [x] `docs/ARCHITECTURE.md` — System architecture, folder layout, and retain/refactor/replace matrix
- [x] `docs/DECISIONS.md` — Architectural Decision Records (ADR-001 through ADR-006)
- [x] `docs/MIGRATION_PLAN.md` — Phased migration strategy
- [x] `docs/KNOWN_LIMITATIONS.md` — Operational, DRM, and platform bounds
- [x] `docs/TEST_REPORT.md` — Baseline environment and toolchain report

## 4. Work in Progress / Next Phase
- **Next Phase:** **Phase 2: Decoupled Media Engine & Structured JSONL IPC**
- Target Milestones:
  1. Patch path traversal in `app/routes/files.py` and sanitize exception handling in `app/main.py`.
  2. Implement `app/engine/protocol.py` (strongly-typed IPC commands and events).
  3. Implement `app/engine/sidecar.py` (stdio JSON Lines runner with non-blocking event streaming).
  4. Refactor `app/services/yt_service.py` to support deep URL analysis, stream listing, audio/video separation, and progress callbacks.
