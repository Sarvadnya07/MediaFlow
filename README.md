# MediaFlow

> A modern, resilient, high-performance media downloader and local media management engine. MediaFlow is engineered as a secure, cross-platform dual-topology system: a standalone native desktop application with a zero-listening-port sidecar architecture, and an optional distributed headless server with Celery workers and FastAPI.

---

## 1. Table of Contents
1. [Project Overview](#2-project-overview)
2. [Key Capabilities & Features](#3-key-capabilities--features)
3. [Implementation Status](#4-implementation-status)
4. [System Architecture & Topologies](#5-system-architecture--topologies)
5. [Prerequisites & System Requirements](#6-prerequisites--system-requirements)
6. [Desktop Application Quickstart](#7-desktop-application-quickstart)
7. [Headless Server Quickstart (Docker & Local)](#8-headless-server-quickstart-docker--local)
8. [Configuration & Environment Reference](#9-configuration--environment-reference)
9. [API Overview & WebSocket Protocol](#10-api-overview--websocket-protocol)
10. [FFmpeg & Transcoding Presets](#11-ffmpeg--transcoding-presets)
11. [Testing & Quality Verification](#12-testing--quality-verification)
12. [Security, Threat Model & Privacy](#13-security-threat-model--privacy)
13. [Troubleshooting & Diagnostics](#14-troubleshooting--diagnostics)
14. [Contributing Guidelines](#15-contributing-guidelines)
15. [License & Disclaimers](#16-license--disclaimers)

---

## 2. Project Overview
**MediaFlow** is a modern media acquisition, transcoding, and library management platform. It combines the universal extraction capabilities of `yt-dlp` and media processing capabilities of `FFmpeg` with a modern React 19 UI and a lightweight Rust/Tauri supervisor.

### Core Value Propositions:
- **Zero Local Attack Surface**: In Desktop mode, the backend runs as an isolated child process using standard I/O (stdio JSON Lines), binding zero local network ports.
- **Resilient Pipeline**: Atomic downloads using temporary `.part` files, rate-limited per-domain dispatch, exponential backoff with jitter, and pause/resume support.
- **Dual Deployment Flexibility**: Deploy as a single native desktop binary or as a multi-container Docker cluster for automated background ingestion.

---

## 3. Key Capabilities & Features

### Media Extraction & Providers
- **Universal Provider Registry**: Automatically inspects input links and routes them to `yt-dlp` or a dedicated direct HTTP/HTTPS streaming parser.
- **Direct HTTP/HTTPS Media**: Verifies MIME types and checks `Accept-Ranges` byte-range headers to confirm multi-threaded chunk support.
- **Rich Metadata Extraction**: Extracts resolutions up to 4K/8K, audio streams with bitrates, thumbnails, full chapter timelines, and multilingual subtitles.

### Processing & Conversion
- **FFmpeg Automation**: Automated remuxing, video transcoding (`mp4`, `mkv`, `webm`), and audio extraction (`mp3`, `aac`, `flac`, `wav`, `m4a`) using structured arguments (`shell=False`).
- **Title Normalization**: Heuristic cleanup that strips clickbait qualifiers, brackets, and resolution tags from output filenames.

### Desktop Integration & UX
- **Seven Dedicated Views**: Analysis, Active Queue, Local Library, Converter, Automation, Diagnostics, and Settings.
- **Automation Tools**: System clipboard watcher, drag-and-drop link dropping, and scheduled nighttime download windows.
- **Local Persistence**: Zero-downtime SQLite WAL storage (`mediadock_queue.db`, `mediadock_library.db`) and frontend state preservation via `localStorage`.

---

## 4. Implementation Status

To provide engineering clarity, features are categorized by current status:

| Capability | Status | Notes |
| :--- | :--- | :--- |
| **Tauri 2 Desktop Shell + React 19 UI** | :white_check_mark: **Implemented** | Tabbed views, local storage settings, IPC bridge. |
| **Python Stdio Sidecar Engine** | :white_check_mark: **Implemented** | Subprocess supervisor communicating over JSON Lines. |
| **yt-dlp Universal Extraction** | :white_check_mark: **Implemented** | Resolves streams, formats, chapters, and metadata. |
| **Direct HTTP Stream Ingestion** | :white_check_mark: **Implemented** | Range headers, size detection, chunked fetching. |
| **Resilient Download Queue** | :white_check_mark: **Implemented** | Priority queue, atomic `.part` promotions, pause/resume. |
| **FFmpeg Audio Extraction & Conversion** | :white_check_mark: **Implemented** | High-bitrate audio rips and format remuxing. |
| **Security URL Filter & SSRF Guard** | :white_check_mark: **Implemented** | RFC 1918 blocking, DNS rebinding guards, containment. |
| **FastAPI REST API & WebSockets** | :white_check_mark: **Implemented** | Headless endpoints for extract, queue, status, and tokens. |
| **Celery + Redis Worker Architecture** | :white_check_mark: **Implemented** | Async task distribution defined in `docker-compose.yml`. |
| **S3 Cloud Storage Offloader** | :large_orange_diamond: **Partially Implemented** | Config flags present; direct local filesystem storage is primary. |
| **Multi-Worker Auto-Scaling** | :white_circle: **Planned** | Dynamic Kubernetes/swarm horizontal worker autoscaling. |
| **P2P Torrent Ingestion** | :x: **Not Planned** | Explicitly out of scope; focus is on HTTP/yt-dlp streams. |

---

## 5. System Architecture & Topologies

MediaFlow operates in one of two configurations:

### Desktop Mode (Zero Network Exposure)
```
[React 19 Frontend]
       │
   (Tauri IPC)
       ▼
[Rust Supervisor (Tauri 2)]
       │
 (Standard I/O JSON Lines)
       ▼
[Python Sidecar Engine] ─── (SQLite WAL)
       │
 [yt-dlp / FFmpeg]
```

### Headless Server Mode (Distributed Services)
```
[Client / UI] ─── HTTP / WS ───► [FastAPI API Gateway]
                                          │
                                    (Redis Broker)
                                          │
                                          ▼
                                 [Celery Worker Cluster]
                                          │
                                 [PostgreSQL / SQLite]
```

Detailed architectural diagrams and state flow specifications are available in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 6. Prerequisites & System Requirements

Ensure the following runtimes and tools are installed:

- **Python**: Version `3.11` or higher.
- **FFmpeg**: Version `4.4` or higher (available on system `PATH`).
- **Node.js**: Version `20+` LTS and `npm`.
- **Rust Toolchain**: `1.78+` (for compiling the Tauri desktop shell).
- **Docker & Compose**: (Optional, required only for containerized headless mode).

---

## 7. Desktop Application Quickstart

Clone the repository and set up your local development environment:

```bash
# 1. Clone repository
git clone https://github.com/your-username/mediaflow.git
cd mediaflow

# 2. Set up Python virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements-dev.txt

# 4. Install Frontend dependencies
cd frontend
npm install

# 5. Launch MediaFlow Desktop in Development Mode
npm run tauri dev
```

---

## 8. Headless Server Quickstart (Docker & Local)

### Running with Docker Compose (Recommended for Headless)
```bash
# Copy and review configuration
cp .env.example .env

# Build and start services in the background
docker compose up -d --build

# Inspect service logs
docker compose logs -f api
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/docs` (returns 200 OK)

### Running Locally without Docker
```bash
# Apply database migrations
alembic upgrade head

# Start API gateway
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 9. Configuration & Environment Reference

MediaFlow loads settings from environment variables or a `.env` file via `app/config.py`. Key configuration options include:

| Environment Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `MediaFlow` | Display title for OpenAPI and log outputs. |
| `DEBUG` | `False` | Verbose debug output and stack trace exposure. |
| `SECRET_KEY` | *(Set in `.env`)* | JWT signing secret for API authentication. |
| `DATABASE_URL` | `sqlite:///./downloads.db` | Target SQLAlchemy database URI. |
| `REDIS_URL` | `redis://localhost:6379/0` | Message broker URI for Celery tasks. |
| `DOWNLOADS_DIR` | `downloads` | Local path where downloads and temporary files are kept. |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Maximum concurrent downloads executed simultaneously. |

For the full reference and examples, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md) and [.env.example](.env.example).

---

## 10. API Overview & WebSocket Protocol

### Primary REST Endpoints
- `POST /api/v1/auth/token`: Generate JWT bearer token for authentication.
- `POST /api/v1/extract`: Analyze URL, return resolutions, audio streams, and chapters.
- `POST /api/v1/download`: Queue a media download job.
- `GET /api/v1/status/{task_id}`: Poll status, speed, percentage, and completion path.

### Real-time WebSocket Updates
- Connect to `ws://localhost:8000/ws/downloads` to receive live JSON progress events without polling.

Full endpoint schemas, request/response bodies, and status codes are documented in [docs/API.md](docs/API.md).

---

## 11. FFmpeg & Transcoding Presets

MediaFlow uses `FFmpeg` with structured arguments (`shell=False`) to avoid command-injection risks:
- **Audio Extraction**: Extracts pristine audio streams to MP3, AAC, FLAC, or WAV with selectable bitrates (up to 320 kbps).
- **Video Remuxing**: Fast remuxing (`-c copy`) without lossy re-encoding when source formats permit.
- **Subtitle Embedding**: Integrates multilingual subtitles directly into container metadata (`.mp4`, `.mkv`).

---

## 12. Testing & Quality Verification

MediaFlow maintains automated unit and integration tests across Python, TypeScript, and Rust:

```bash
# Run deterministic Python unit tests (offline mode)
pytest -q -m "not network" tests/

# Run complete Python test suite including online external stream checks
pytest -q tests/

# Run React frontend tests (Vitest)
cd frontend
npx vitest run

# Run Tauri Rust supervisor unit tests
cargo test --lib --manifest-path src-tauri/Cargo.toml
```

All 79 tests across the repository pass consistently.

---

## 13. Security, Threat Model & Privacy

MediaFlow enforces security boundaries across all execution layers:
1. **SSRF & DNS Rebinding Protection**: User-submitted URLs undergo pre-dispatch DNS resolution. Loopback IPs (`127.0.0.1`), RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and non-HTTP schemes are blocked.
2. **Path Traversal Containment**: Output file paths are verified against `DOWNLOADS_DIR` via canonical path resolution (`relative_to`).
3. **No DRM Tampering**: MediaFlow strictly interacts with public, unencrypted streams supported by `yt-dlp`. It does not decrypt or bypass DRM systems (Widevine, FairPlay, PlayReady).
4. **No Cookie Scraping**: MediaFlow does not access or harvest user browser cookies or credentials without intentional user configuration.

For complete vulnerability reporting instructions, review [SECURITY.md](SECURITY.md).

---

## 14. Troubleshooting & Diagnostics

- **`ffmpeg: command not found`**: Ensure `ffmpeg` and `ffprobe` are installed and available on your system `PATH`.
- **Port Conflict in Headless Mode**: If port 8000 or 5432 is in use, modify port bindings in `docker-compose.yml`.
- **Database Lock on SQLite**: Verify no lingering zombie Python sidecars remain. MediaFlow configures SQLite in WAL mode with a 5000ms busy timeout.
- **Diagnostics View**: In Desktop mode, navigate to the **Diagnostics** tab to review real-time sidecar heartbeat, memory footprint, and disk metrics.

For step-by-step installation troubleshooting, see [docs/INSTALLATION.md](docs/INSTALLATION.md).

---

## 15. Contributing Guidelines

We welcome community contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before submitting pull requests.

1. Create a feature branch from `main`.
2. Ensure all linters and tests pass (`pytest -m "not network"`, `npx vitest run`, `cargo test`).
3. Submit a PR using our structured pull request template.

---

## 16. License & Disclaimers

This project is licensed under the [MIT License](LICENSE).

**Disclaimer**: MediaFlow is intended for downloading and managing content that you own or have lawful permission to access. MediaFlow contributors assume no liability for misuse contrary to copyright law or platform terms of service.
