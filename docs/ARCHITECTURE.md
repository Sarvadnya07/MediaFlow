# MediaFlow — System Architecture & Topology Guide

MediaFlow is designed as a modular, dual-topology media acquisition and management system. It supports both a self-contained local desktop application (optimized for security and zero open network ports) and a scalable headless/containerized server mode (optimized for headless background workers and team workflows).

---

## 1. High-Level Architectural Topologies

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TOPOLOGY A: DESKTOP APP                         │
│                                                                        │
│  ┌───────────────────────┐             ┌────────────────────────────┐  │
│  │   React 19 Frontend   │             │   Tauri 2 Core (Rust)      │  │
│  │  (TypeScript, Tailwind)├────────────►│  Supervisor, Tray, Dialogs │  │
│  └───────────────────────┘  Tauri IPC  └─────────────┬──────────────┘  │
│                                                      │                 │
│                                     Standard I/O     │ (JSON Lines)    │
│                                                      ▼                 │
│                                        ┌────────────────────────────┐  │
│                                        │   Python Sidecar Engine    │  │
│                                        │  yt-dlp, FFmpeg, SQLite WAL│  │
│                                        └────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│                        TOPOLOGY B: HEADLESS SERVER                     │
│                                                                        │
│  ┌───────────────────────┐             ┌────────────────────────────┐  │
│  │   HTTP / WS Clients   ├────────────►│     FastAPI Gateway        │  │
│  │  (REST API, WebSockets)│  HTTP/WS   │    (Auth, Routers, DB)     │  │
│  └───────────────────────┘             └─────────────┬──────────────┘  │
│                                                      │                 │
│                                     Redis Queue      │ Celery Tasks    │
│                                                      ▼                 │
│                                        ┌────────────────────────────┐  │
│                                        │    Celery Worker Nodes     │  │
│                                        │  yt-dlp Engine, FFmpeg     │  │
│                                        │  PostgreSQL Persistence    │  │
│                                        └────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems

### A. Media Acquisition Pipeline
- **Provider Registry (`app/core/providers/`)**:
  - `BaseProvider`: Abstract contract for media extraction.
  - `UniversalYtDlpProvider`: Wraps `yt-dlp` to extract formats, resolutions, audio streams, and chapters across 1,000+ supported public domains.
  - `DirectHttpProvider`: Analyzes direct HTTP/HTTPS media streams (`.mp4`, `.mp3`, `.mkv`), inspecting MIME types and querying `Accept-Ranges` byte-range headers.
- **Download Coordinator (`app/core/queue/`)**:
  - Priority scheduling: Prioritizes active downloads based on user priority levels.
  - Per-Domain Rate Limiting: Prevents IP throttling and socket exhaustion by capping concurrent downloads per host.
  - Resilient Download Engine: Writes to atomic `.part` temporary files, auto-resumes interrupted streams, and applies exponential backoff with jitter on transient network drops.

### B. Media Processing & FFmpeg Integration (`app/services/processing.py`)
- Standardized execution with `shell=False`.
- Transcoding presets:
  - Video remuxing and re-encoding (`mp4`, `mkv`, `webm`).
  - Audio extraction (`mp3`, `aac`, `flac`, `wav`, `m4a`) with configurable bitrates (`320k`, `256k`, `192k`).
  - Subtitle embedding or standalone extraction (`srt`, `vtt`).

### C. State Ownership & Data Storage
- **Desktop Mode**: Uses SQLite in Write-Ahead Logging (WAL) mode (`mediadock_queue.db`, `mediadock_library.db`).
  - PRAGMAs: `synchronous = NORMAL`, `journal_mode = WAL`, `busy_timeout = 5000`.
  - Zero listening network ports; all IPC communicates via `stdin`/`stdout`.
- **Headless Server Mode**: Uses SQLAlchemy 2.0 with PostgreSQL or SQLite. Migrations managed by Alembic.

---

## 3. Directional Flow & Architecture Fitness
The Python media engine enforces a strict single-direction dependency DAG:
`models` ➔ `schemas` ➔ `services` ➔ `routes` / `worker`

Circular dependencies and cross-boundary leaks are disallowed and validated via automated AST tests (`tests/test_architecture_fitness.py`).
