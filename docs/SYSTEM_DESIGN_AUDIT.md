# 🏛️ ARCH-01 — Forensic Architecture & System Design Audit

**System:** MediaDock / `yt_dlp_backend`  
**Lead Architect:** Principal Software Architect & Systems Engineering Reviewer  
**Date:** 2026-11-08  
**Audit Scope:** Complete forensic audit of the existing repository architecture, deployment topology, coupling, data ownership, quality attributes, and desktop evolution.

---

## 1. Executive Architecture Assessment

The existing codebase (`yt_dlp_backend`) originated as a multi-container server application designed around FastAPI, Celery, Redis, and SQLAlchemy. It was intended to run as a centralized web service where users authenticate via JWT, submit video download tasks over HTTP, and poll for progress or subscribe via Redis-backed WebSockets, with downloads stored in a local directory or mapped volume.

### Architectural Reality vs Stated Purpose:
1. **The Distributed Monolith Anti-Pattern on SQLite:** In its server configuration (`docker-compose.yml`), both the `api` and `worker` containers mount and write concurrently to the same local SQLite file (`downloads.db`). While SQLite supports WAL mode, sharing an SQLite file across separate Linux containers via host volume mounts creates serious lock contention, cross-process corruption risks, and file lock invalidation.
2. **Coupling to Heavy Infrastructure:** To download a video on a local desktop machine, the original architecture required:
   - A Redis daemon (in-memory key-value broker & pubsub).
   - A Celery background worker daemon.
   - A Uvicorn HTTP application server listening on TCP port 8000.
   - An unauthenticated or loosely authenticated local HTTP/WebSocket loopback interface.
   For a desktop application, this introduces severe friction: port conflicts, firewall alerts, high baseline RAM usage (~250MB+ idle for Redis + Celery + Python), and orphan background processes when the user exits the GUI.
3. **Engine Capabilities vs UI Integration:** The core domain logic (`yt-dlp` and `FFmpeg` execution) is fundamentally robust, high-value, and cross-platform. However, the business logic was initially entangled with HTTP request lifecycles (`fastapi.Depends`), Celery `@celery.task` decorators, and raw database transactions.
4. **Desktop Transformation Trajectory:** The decoupling executed in Phase 2 successfully liberated the core media engine (`app/services/yt_service.py`, `app/services/ffmpeg_service.py`, `app/engine/protocol.py`, `app/engine/sidecar.py`) from network brokers, establishing a high-cohesion, low-coupling stdio JSON Lines IPC boundary that enables native Tauri 2 desktop execution without sacrificing headless server mode.

---

## 2. Requirements & Quality Attributes

### Functional Requirements
- **FR-1: URL Media Analysis:** Discover available media streams, resolutions, codecs, audio bitrates, and subtitles (author and automated) without downloading content.
- **FR-2: Flexible Media Acquisition:** Download specific stream IDs or composite streams (`bestvideo+bestaudio`), extract thumbnails, and convert subtitle streams to SRT.
- **FR-3: Media Post-processing & Conversion:** Convert video to audio (`mp3`, `flac`, `wav`, `opus`) and re-encode video containers cleanly using FFmpeg.
- **FR-4: Queue & Progress Orchestration:** Provide real-time, non-blocking percentage, transfer rate, and ETA metrics with cooperative cancellation.
- **FR-5: History & Settings Persistence:** Maintain durable records of downloaded files, status, filepaths, and user preferences.

### Quality Attribute Constraints & Trade-Offs

| Quality Attribute | Architectural Requirement | Current State / Finding | Evolution Driver |
|---|---|---|---|
| **Latency** | Immediate interactive response (<100ms for analysis, immediate progress events). | Server mode: WebSocket over Redis PubSub introduces multi-hop latency.<br>Desktop mode: Direct stdio JSONL IPC gives sub-millisecond event dispatch. | Stdio IPC eliminates network stack overhead. |
| **Throughput / Concurrency** | Non-blocking execution of multiple concurrent downloads without thread starvation. | Celery concurrency limited by prefork pool.<br>Desktop: Tokio async supervisor in Tauri orchestrating Python thread workers. | Avoids heavy OS process duplication. |
| **Availability & Fault Isolation** | Media engine failure/crash must never crash the UI or corrupt user history. | In server mode, worker crash silently fails tasks if unhandled.<br>In desktop sidecar mode, child process restart is managed by Tauri supervisor. | Process sandboxing isolates UI from Python engine faults. |
| **Durability & Consistency** | Zero state loss upon crash or cancellation; no orphaned partial files. | SQLite WAL mode enabled; partial downloads need cleanup hooks on cancel/crash. | WAL mode allows concurrent reads without locking writes. |
| **Security & Privacy** | Zero credential collection, no SSRF, strict filesystem sandboxing, no cookie theft. | Mitigated: SSRF validator, directory containment, and sanitization implemented in Phase 2. | Least-privilege local execution. |
| **Operability & Footprint** | Low idle memory (<80MB for desktop), zero daemon installation prerequisites. | Server mode failed this (required Redis + Celery).<br>Desktop mode succeeds: zero-dependency bundled runtime. | Eliminates Redis/Celery from desktop footprint. |

---

## 3. Current Architecture Map

```mermaid
flowchart TD
    subgraph UI_Layer ["Presentation Tier"]
        DesktopUI["Tauri Webview (React + Vite + Tailwind)"]
        ServerUI["External HTTP / API Clients"]
    end

    subgraph Host_Gateway ["Desktop Shell / Gateway"]
        TauriHost["Tauri 2 Core (Rust / Tokio)"]
        FastAPIHost["FastAPI Application Server (Uvicorn)"]
    end

    subgraph IPC_Broker ["Inter-Process Communication"]
        StdioPipe["Stdio JSON Lines Pipe"]
        RedisPubSub["Redis 7 (Broker & Pub/Sub)"]
    end

    subgraph Engine_Core ["Media Engine (Python 3.12/3.13)"]
        Sidecar["Sidecar Runner (app.engine.sidecar)"]
        CeleryWorker["Celery Worker Tasks (app.worker.tasks)"]
        YtService["yt_service (Pure Core Engine)"]
        FFmpegService["ffmpeg_service (Subprocess CLI)"]
    end

    subgraph Storage_Layer ["Persistence & External"]
        SQLiteDB[("SQLite (downloads.db) WAL Mode")]
        Filesystem[("Local Filesystem (downloads/)")]
        FFmpegBin["FFmpeg / FFprobe Binaries"]
        RemoteHosts["Media Streaming Hosts"]
    end

    DesktopUI <-->|Tauri IPC Commands / Events| TauriHost
    TauriHost <-->|JSON Lines (stdin/stdout)| StdioPipe
    StdioPipe <--> Sidecar
    Sidecar --> YtService
    Sidecar --> FFmpegService

    ServerUI <-->|HTTP / WebSockets| FastAPIHost
    FastAPIHost --> RedisPubSub
    RedisPubSub --> CeleryWorker
    CeleryWorker --> YtService
    CeleryWorker --> FFmpegService

    YtService --> SQLiteDB
    YtService --> Filesystem
    YtService --> RemoteHosts
    FFmpegService --> FFmpegBin
```

---

## 4. Architectural Style & Style Fit Analysis

### Detected Styles
1. **Desktop Deployment Mode:** **Process-Isolated Sidecar Architecture (Pipe-and-Filter / Event-Driven IPC)**.
   - *Why it fits:* It separates the native desktop lifecycle (Rust/Tauri) and UI responsiveness (React) from the Python runtime and external media scraping tools (`yt-dlp`).
   - *Benefits:* High fault isolation; Python crashes do not bring down the UI; no open network ports; zero dependency on external server infrastructure.
   - *Costs:* Serialization/deserialization over stdio JSON Lines; process lifecycle supervision required in Rust.
2. **Server Deployment Mode:** **Layered Micro-Service / Distributed Asynchronous Monolith**.
   - *Why it exists:* Designed for multi-tenant web API with decoupled asynchronous worker queues.
   - *Costs:* High operational burden (Redis, Celery, volume mounts); unnecessary complexity for desktop single-user operation.

---

## 5. Module & Domain Boundary Audit

| Module | Boundary Type | Responsibility | Cohesion | Coupling | Assessment |
|---|---|---|---|---|---|
| `app/engine/protocol.py` | Contract / Schema | IPC Request, Response, Event models | **High** | **Low** | Pristine. Clean Pydantic data boundary. |
| `app/engine/sidecar.py` | Runtime Adapter | Stdio JSONL event loop runner | **High** | **Low** | High cohesion. Decoupled from HTTP and DB. |
| `app/services/yt_service.py` | Domain Service | URL analysis, format resolution, download hooks | **High** | **Low** | Refactored in Phase 2 into pure functional engine. |
| `app/services/ffmpeg_service.py` | Domain Service | Audio conversion, video re-encoding, metadata | **High** | **Low** | Self-contained, robust binary resolution. |
| `app/security.py` | Cross-Cutting | SSRF filtering, filename sanitization, containment | **High** | **Low** | Universal utility protecting all ingestion. |
| `app/models.py` | Persistence Entity | SQLAlchemy Download & User entities | **Medium** | **Medium** | Clean, shared across SQLite migrations. |
| `app/routes/` | Presentation (Server) | REST API endpoints | **Medium** | **High** | Tightly coupled to FastAPI and Celery. |
| `app/worker/` | Worker (Server) | Celery task handlers & Redis publishing | **Medium** | **High** | Heavy server coupling; kept isolated. |

---

## 6. Detailed Architectural Findings

```text
ID: ARCH-FIND-01
Area: Storage & Concurrency
Architectural Decision: Multi-process concurrent write to single SQLite file over Docker volumes.
Current State: Both FastAPI container and Celery worker container mount and write to downloads.db.
Requirement / Quality Attribute: Durability, Consistency, Operability.
Evidence: docker-compose.yml lines 17-21 and 31-35.
Problem: SQLite over network/docker host volume mounts lacks reliable POSIX advisory file locking, risking "database is locked" errors and potential page corruption under concurrent writes.
Impact: Server instability under load; high operational fragility.
Trade-off: Avoided running PostgreSQL in favor of zero-config SQLite.
Risk: Database corruption or locked transactions during concurrent downloads.
Recommended Direction: For server mode, switch to PostgreSQL (already supported by SQLAlchemy). For desktop mode, access SQLite strictly through Tauri host process or single-owner engine connection with WAL enabled.
Migration Complexity: Low.
Operational Impact: Eliminates SQLite volume locking failures.
Team Impact: None.
Validation Method: Run concurrent write stress test across 5 worker threads.
Priority: 🔴 CRITICAL (for Server Docker mode)
```

```text
ID: ARCH-FIND-02
Area: Inter-Process Communication & Attack Surface
Architectural Decision: Running local HTTP server + Redis for single-user desktop media downloading.
Current State: Historical architecture required Uvicorn HTTP server on port 8000 and Redis on port 6379.
Requirement / Quality Attribute: Security, Resource Efficiency, Footprint.
Evidence: README.md, docker-compose.yml.
Problem: Unauthenticated local HTTP servers open local loopback attack surface (DNS rebinding, drive-by web requests from malicious browser tabs). Requires local Redis installation.
Impact: Desktop deployment failure on user machines without Redis; OS firewall prompts.
Trade-off: Fast initial prototyping using web stack vs native desktop design.
Risk: Rejection by desktop users; security vulnerabilities.
Recommended Direction: Completely replace local HTTP/Redis communication on desktop with managed Tauri stdio JSON Lines IPC. Retain Celery/Redis strictly for headless server mode.
Migration Complexity: Medium.
Operational Impact: Desktop runs out-of-the-box with zero background daemons.
Team Impact: Clean separation between desktop app and server engine.
Validation Method: Verify desktop runs and downloads without Redis or Uvicorn running.
Priority: 🔴 CRITICAL
```

```text
ID: ARCH-FIND-03
Area: Domain Logic Encapsulation
Architectural Decision: Direct database writes inside Celery worker tasks instead of domain service.
Current State: app/worker/tasks.py directly creates SessionLocal(), mutates Download attributes, and commits.
Requirement / Quality Attribute: Maintainability, Separation of Concerns, Reusability.
Evidence: app/worker/tasks.py lines 15-90.
Problem: Business logic for state transitions (PENDING -> PROCESSING -> COMPLETED) is duplicated between worker tasks and HTTP routes.
Impact: Inconsistent state transitions if another caller invokes yt_service directly.
Trade-off: Expedient script implementation.
Risk: Divergent state and metadata schemas across different runners.
Recommended Direction: Centralize download lifecycle state transitions into a dedicated queue/persistence manager.
Migration Complexity: Low.
Operational Impact: Simplifies future extensions and testing.
Team Impact: Unified code path.
Validation Method: Unit tests verifying state machine transitions.
Priority: 🟡 MEDIUM
```

```text
ID: ARCH-FIND-04
Area: AI Enrichment Coupling
Architectural Decision: AI summarization mock tightly coupled in task execution path.
Current State: tasks.py synchronously invokes ai_service.summarize_video and generate_tags in task completion handler.
Requirement / Quality Attribute: Modularity, Fault Isolation, Performance.
Evidence: app/worker/tasks.py lines 60-66.
Problem: ai_service is currently a static mock. In a production scenario with real LLM API calls, synchronous execution in the download completion hook introduces network latency, token consumption, and failure modes.
Impact: Download completion delayed or failed by external AI service outage.
Trade-off: Demonstration feature vs real production decoupling.
Risk: External API timeouts delaying download completion events.
Recommended Direction: Make AI enrichment an explicit, optional, asynchronous post-processing pipeline triggered only on user request.
Migration Complexity: Low.
Operational Impact: Zero latency penalty on core downloads.
Team Impact: Clean plugin boundary for AI features.
Validation Method: Benchmark download completion with and without AI enrichment enabled.
Priority: 🔵 LOW
```

---

## 7. Strengths Worth Preserving

1. **`yt-dlp` Foundation:** Unmatched extractor coverage across virtually all global streaming providers.
2. **FFmpeg Subprocess Pipeline:** Direct argument list execution avoiding shell expansion vulnerabilities (`shell=False`).
3. **Pydantic Validation Discipline:** Strict request/response validation across all domain boundaries.
4. **Alembic Database Migration Lineage:** Clean revision history enabling predictable schema upgrades without data loss.
5. **Phase 2 Decoupled Engine:** Pure functional core (`analyze_url`, `download_stream`, cancellation tokens) and robust stdio JSONL protocol (`app.engine.protocol`, `app.engine.sidecar`).

---

## 8. Prioritized Architecture Roadmap

| Milestone | Action | Priority | Target Phase |
|---|---|---|---|
| **M1: Desktop Host & Supervisor** | Build Tauri 2 Rust supervisor managing Python sidecar stdio pipe, heartbeat, and graceful shutdown. | 🔴 CRITICAL | Phase 3 (Active) |
| **M2: In-Process Queue Manager** | Implement Rust-based Tokio download queue replacing Celery/Redis for desktop. | 🟠 HIGH | Phase 3/4 |
| **M3: Modern Desktop UI** | Build React + Vite + Tailwind CSS + shadcn/ui multi-panel interface. | 🟠 HIGH | Phase 3/4 |
| **M4: Safe Database Access** | Enforce single-owner SQLite connection with WAL mode in desktop runtime. | 🟡 MEDIUM | Phase 4 |
| **M5: Headless Server Isolation** | Retain Docker Compose / Celery / FastAPI mode as an independent headless server deployment target. | ⚪ CONTEXTUAL | Maintenance |
