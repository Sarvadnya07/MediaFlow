# MediaDock — Build Status & Task Tracker

## 1. Project Overview
MediaDock is a modern, cross-platform desktop media management and download suite upgrading the existing `yt_dlp_backend` engine into a Tauri 2 + Rust desktop architecture with a React + TypeScript frontend and a Python + yt-dlp IPC sidecar.

## 2. Current Implementation State
- **Phase 1: Deep Repository Audit:** COMPLETED (`ec7b3e6`)
- **Phase 2: Backend Refactoring & Sidecar Protocol:** COMPLETED (`ccf70e8`)
- **Phase 3: Desktop Application Foundation & ARCH-01 Audit:** COMPLETED (`1f69676`)
- **Phase 4: Complete Core Downloader & File Verification:** **COMPLETED & VERIFIED**.
  - **Working Branch:** `feat/phase-4-core-downloader`
  - **URL Input & Navigation:**
    - Paste from clipboard, URL validation, clear input, and recent URL history chips.
  - **Media Analysis & Format Filtering:**
    - Displays genuine metadata: title, uploader/channel, extractor, duration, and thumbnail.
    - Dynamic stream selector separating video+audio streams from audio-only streams.
    - Real resolution, container, frame rate, and estimated file size display.
    - Author subtitle and automatic caption selector.
  - **Download Orchestration & Real Progress:**
    - Non-blocking download execution via Rust `start_download` command to Python engine sidecar.
    - Real-time progress forwarding via Tauri events: percent, transfer rate, ETA, downloaded bytes.
    - Cooperative thread cancellation support (`cancel_job`).
  - **Post-Download File Verification:**
    - `verify_media_file` implemented in `app/services/ffmpeg_service.py` using `ffprobe`.
    - Validates file existence, non-zero byte size, stream codecs, container structure, and duration.
  - **Acceptance Testing:**
    - Completed real authorized media download and FFprobe verification in `tests/test_download_verification.py`.
    - Total test suite: **24/24 passing across Rust, Python, and TypeScript**.

## 3. Mandatory Governance Artifacts
- [x] `BUILD_STATUS.md` — Active tracker
- [x] `docs/SYSTEM_DESIGN_AUDIT.md` — Forensic ARCH-01 Architecture & System Design Audit
- [x] `docs/PROJECT_AUDIT.md` — Historical audit verification and security assessment
- [x] `docs/ARCHITECTURE.md` — System architecture and IPC contract design
- [x] `docs/DECISIONS.md` — Architectural Decision Records (ADR-001 through ADR-006)
- [x] `docs/MIGRATION_PLAN.md` — Phased migration strategy
- [x] `docs/KNOWN_LIMITATIONS.md` — Platform, DRM, and temporary disk constraints
- [x] `docs/TEST_REPORT.md` — Automated test report (24 passing tests)

## 4. Next Phase
- **Phase 5: Persistent Download History, SQLite Integration & Desktop Polishing:**
  - Connect SQLite history view to display completed files with direct "open folder" shortcuts.
  - Enable customizable download directory and concurrency throttling in Settings view.
