# MediaDock System Architecture

## 1. Executive Summary
MediaDock evolves the existing `yt_dlp_backend` Python/FastAPI/Celery codebase into a high-performance, secure desktop application. Instead of exposing an unauthenticated or loosely authenticated local HTTP server or spawning raw shell commands, MediaDock uses a structured, sandboxed sidecar architecture.

```mermaid
flowchart TD
    subgraph Presentation ["Presentation Layer (Webview)"]
        UI["React 18 + TypeScript + Vite"]
        TW["Tailwind CSS + shadcn/ui"]
        FM["Framer Motion + Lucide"]
    end

    subgraph DesktopHost ["Desktop Shell (Tauri 2 + Rust)"]
        TR["Tauri Core Host"]
        StateMgr["Download & Queue Manager"]
        SqliteConn["Native SQLite Store / Migrations"]
        IPC["Process Stdio Pipe (JSON Lines IPC)"]
    end

    subgraph EngineSidecar ["Media Engine (Python Sidecar)"]
        Runner["media_sidecar.py (IPC Loop)"]
        YtService["yt_service / yt-dlp Core"]
        Extractor["Metadata & Format Resolver"]
        ProgressHook["Real-time Progress Dispatcher"]
    end

    subgraph External ["System Tools & Network"]
        FFmpegBin["FFmpeg / FFprobe"]
        WebProviders["Media Hosts / Authorized Streams"]
    end

    UI <-->|Tauri IPC Commands / Events| TR
    TR --> StateMgr
    StateMgr --> SqliteConn
    TR <-->|JSON Lines (stdin / stdout)| IPC
    IPC <--> Runner
    Runner --> YtService
    YtService --> Extractor
    YtService --> ProgressHook
    ProgressHook -->|Progress Events JSONL| Runner
    YtService --> FFmpegBin
    YtService --> WebProviders
```

## 2. Current Folder Architecture vs Proposed Upgrade Architecture

### Current Structure:
```
yt_dlp_backend/
├── .env                  (Untracked from git index in Phase 1)
├── .env.example          (Added Phase 1)
├── .gitignore            (Hardened Phase 1)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
├── alembic/              (Database migration scripts)
│   └── versions/
├── app/
│   ├── auth.py           (JWT authentication for REST API)
│   ├── config.py         (Pydantic settings)
│   ├── database.py       (SQLAlchemy session engine)
│   ├── logging_config.py (JSON formatter & logger)
│   ├── main.py           (FastAPI entrypoint)
│   ├── models.py         (SQLAlchemy User & Download models)
│   ├── rate_limiter.py
│   ├── schemas.py        (Pydantic schemas)
│   ├── routes/           (auth, downloads, files, websockets)
│   ├── services/         (yt_service, ffmpeg_service, ai_service, storage_service)
│   └── worker/           (Celery app and background tasks)
└── docs/                 (Architecture, Decisions, Audit, Status)
```

### Proposed Upgrade Structure:
```
yt_dlp_backend/
├── .env.example
├── .gitignore
├── requirements.txt      (Includes yt-dlp, pydantic, pytest)
├── alembic/              (Preserved for database migrations)
├── app/
│   ├── engine/           (NEW: Dedicated desktop sidecar IPC package)
│   │   ├── __init__.py
│   │   ├── protocol.py   (Strongly-typed IPC request/response models)
│   │   └── sidecar.py    (JSONL stdio event loop runner)
│   ├── services/
│   │   ├── yt_service.py     (Refactored: Pure extraction, format filtering, download hooks)
│   │   └── ffmpeg_service.py (Refactored: Binary detection, progress, postprocessing)
│   ├── models.py         (Preserved SQLAlchemy models for downloads & history)
│   ├── database.py       (SQLite engine)
│   ├── main.py           (Preserved for headless/server mode)
│   └── worker/           (Preserved Celery tasks for server mode)
├── src-tauri/             (NEW: Tauri 2 + Rust Desktop Host)
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── src/
│       ├── main.rs       (Tauri app bootstrap)
│       ├── sidecar.rs    (Process supervisor & stdio JSONL manager)
│       ├── queue.rs      (Desktop in-process download queue)
│       ├── db.rs         (SQLite query & persistence bridge)
│       └── commands.rs   (Tauri command handlers invoked by React)
├── frontend/             (NEW: React + TypeScript + Vite UI)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── components/   (Format selector, Queue list, History table, Player)
│       ├── hooks/        (Tauri event listeners, IPC mutation hooks)
│       ├── lib/          (Tauri API wrappers, utils)
│       └── App.tsx       (Main desktop view layout)
└── docs/                 (System documentation and governance)
```

## 3. Core Components

### 3.1 Tauri 2 (Rust Core)
- **Lifecycle & Process Management:** Spawns and manages the Python sidecar as a child process. Monitors heartbeat, stdout/stderr, and ensures graceful termination upon window close.
- **IPC Gateway:** Exposes strongly-typed Rust commands (`analyze_url`, `start_download`, `pause_download`, `cancel_download`, `get_history`, `update_settings`) to the React frontend.
- **Queue & Download Orchestration:** Replaces heavy Celery/Redis background worker dependencies for desktop usage with an in-process, asynchronous Rust queue worker communicating directly with the Python engine sidecar.
- **Local Persistence:** Manages SQLite database transactions directly or shares schema compatibility with SQLAlchemy models for user history, preferences, and download states.

### 3.2 Python Engine Sidecar
- **Entrypoint:** `app/engine/sidecar.py` (or bundled binary via PyInstaller in production).
- **Communication Protocol:** Strict JSON Lines over `stdin` (requests/commands from Rust) and `stdout` (responses and streaming progress events to Rust).
- **Diagnostic Logging:** All operational logs are directed strictly to `stderr` or rotating log files, preventing contamination of the JSONL communication stream on `stdout`.
- **Core Modules Reused:**
  - `app/services/yt_service.py`: URL metadata extraction, available video/audio format filtering, postprocessor configuration (FFmpeg merging, subtitles, thumbnails).
  - Integration with `yt-dlp` library.

### 3.3 Frontend (React + TypeScript + Vite)
- **Design System:** Tailwind CSS + Radix UI / shadcn/ui.
- **Motion & Micro-interactions:** Framer Motion.
- **State Management:** TanStack Query / Zustand for reactive download progress, active tasks, and history display.
- **Safety:** No direct access to shell or filesystem paths without Tauri permission validation.

## 4. Retain / Refactor / Replace / Remove Decision Matrix

| Item / File | Status | Decision & Action |
|---|---|---|
| `app/services/yt_service.py` | Existing | **REFACTOR:** Decouple from database commits and Celery. Provide pure functional `analyze_url`, `download_stream` with callback hooks. |
| `app/services/ffmpeg_service.py` | Existing | **REFACTOR:** Introduce robust binary location resolution and error handling. |
| `app/models.py` | Existing | **RETAIN:** Retain schema models for downloads history, status, and file attributes. |
| `alembic/` | Existing | **RETAIN:** Keep migration tree for clean schema deployment on SQLite. |
| `app/routes/files.py` | Existing | **REFACTOR:** Patch path traversal vulnerability by strictly resolving and checking containment within `DOWNLOADS_DIR`. |
| `app/main.py` | Existing | **REFACTOR:** Sanitize error messages in global exception handler to prevent leaking internals. |
| `app/worker/celery_app.py` & `tasks.py` | Existing | **RETAIN (Isolate):** Keep intact for headless server deployment; not used in desktop runtime. |
| `app/services/ai_service.py` | Existing | **REPLACE:** Replace static mock with optional, pluggable LLM adapter. |
| `app/services/storage_service.py` | Existing | **REMOVE / ISOLATE:** S3 mock is unnecessary for desktop app; retain local filesystem storage. |
| `app/routes/a.py` | Existing | **REMOVE:** Obsolete scratch file. |
| `fix.py` | Existing | **REMOVE:** Obsolete one-off file rename script. |
| `downloads/*` test videos | Existing | **REMOVE FROM GIT:** 12MB of committed test mp4 binaries removed from Git tracking. |
