# 🧩 BACKEND-01 — Forensic Backend Engineering Audit Report

**System:** MediaDock / `yt_dlp_backend`  
**Lead Auditor:** Principal Backend Engineer & Distributed Systems Architect  
**Date:** 2026-11-08  
**Audit Scope:** Complete forensic audit of the backend implementation across Desktop (IPC sidecar) and Server (FastAPI + Celery) modes, including correctness, business logic, data access, transactions, concurrency, security, and operability.

---

## 1. Executive Backend Assessment

The backend engineering of MediaDock exhibits a dual-mode topology:
1. **Primary Desktop Architecture (Tauri 2 + Python IPC Sidecar):**
   - **Quality State:** **High Excellence (Level 3+ Maturity)**.
   - Operates strictly over bidirectional standard I/O JSON Lines (`stdin`/`stdout`).
   - Strong business rule encapsulation inside dedicated service domains (`DownloadQueueManager`, `MediaLibraryManager`, `ProviderRegistry`, `DiagnosticsService`, `MediaIntelligenceService`).
   - SQLite backed with Write-Ahead Logging (WAL) mode, thread-safe cancellation tokens, and jittered exponential backoff.
   - Comprehensive automated coverage: 63 pytest tests, 3 Rust cargo tests, and 4 architectural fitness functions.
2. **Legacy Headless Server Architecture (FastAPI + Celery + Redis):**
   - **Quality State:** **Functional but Heterogeneous (Level 1 Maturity)**.
   - Retained in `app/routes/`, `app/worker/`, and `docker-compose.yml` for containerized multi-user environments.
   - Contains classic distributed-monolith friction points: multi-container write concurrency to a shared SQLite volume, unbounded Celery task retries, and WebSocket endpoints lacking JWT handshake validation.

---

## 2. Architecture Style & Boundaries

### Current Architecture Style
- **Desktop Runtime:** **Modular Process-Isolated Sidecar Architecture** (Clean separation between Rust Tokio desktop supervisor and Python media execution).
- **Server Runtime:** **Layered Web API with Asynchronous Task Workers** (FastAPI REST endpoints dispatching tasks to Celery via Redis broker).

### Boundary Mapping

```text
┌────────────────────────────────────────────────────────┐
│             Desktop Webview (React 19)                 │
└──────────────────────────┬─────────────────────────────┘
                           │ Tauri IPC (Commands & Events)
┌──────────────────────────▼─────────────────────────────┐
│          Desktop Host Supervisor (Rust / Tokio)        │
│  Commands: list_providers, list_library, enrich_media  │
└──────────────────────────┬─────────────────────────────┘
                           │ Stdio JSON Lines (stdin / stdout)
┌──────────────────────────▼─────────────────────────────┐
│        Sidecar Dispatcher (app/engine/sidecar.py)      │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Provider Registry (app/providers/registry.py)      │ │
│ │  ├── DirectHttpProvider (Direct Static Streams)    │ │
│ │  └── YtDlpProvider (Universal Extractor Fallback)  │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ DownloadQueueManager (SQLite WAL Queue Isolation)  │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ MediaLibraryManager (Contained Catalog Management) │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ MediaIntelligenceService (Heuristic / Chapter Meta)│ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Forensic Findings

```text
ID: BACKEND-FIND-01
Area: Server Authentication / Authorization
Component: app/routes/websockets.py
Current State: WebSocket progress endpoint accepts raw download_id without validating JWT token.
Evidence: app/routes/websockets.py lines 9-11:
  @router.websocket("/progress/{download_id}")
  async def websocket_progress(websocket: WebSocket, download_id: int):
      await websocket.accept()
Requirement: Object-level authorization enforced on every sensitive endpoint.
Problem: Any unauthenticated client knowing a numerical download_id can listen to progress events.
User Impact: Information disclosure of download status and title in server mode.
Security Impact: Medium.
Reliability Impact: Low.
Performance Impact: None.
Maintainability Impact: Low.
Root Cause: Expedient WebSocket setup without handshake token parsing.
Recommended Direction: For server mode, extract JWT query parameter or Authorization header during websocket handshake and assert current_user ownership or admin role.
Implementation Complexity: Low.
Validation Method: Negative test attempting unauthenticated WebSocket connection.
Priority: 🟡 MEDIUM (Server Mode Only; Desktop uses private stdio)
Owner: Backend API Team
```

```text
ID: BACKEND-FIND-02
Area: Server Data Access & Concurrency
Component: docker-compose.yml / app/database.py
Current State: Both FastAPI and Celery containers mount and write concurrently to single downloads.db.
Evidence: docker-compose.yml lines 17-21 and 31-35.
Requirement: Durable, non-conflicting multi-process database transactions.
Problem: SQLite file locking across Docker volume mounts lacks POSIX lock guarantees under concurrent write bursts.
User Impact: "database is locked" errors during heavy server download volume.
Security Impact: None.
Reliability Impact: Medium in multi-container server setup.
Performance Impact: Degraded write throughput.
Maintainability Impact: Medium.
Root Cause: Defaulting to SQLite for both local desktop and multi-container Docker compose.
Recommended Direction: Retain SQLite for desktop runtime; configure PostgreSQL as default DATABASE_URL in docker-compose.yml for server mode.
Implementation Complexity: Low (SQLAlchemy models already support PostgreSQL).
Validation Method: Run concurrent Celery tasks against Docker compose stack.
Priority: 🟡 MEDIUM (Server Mode Only)
Owner: Platform / SRE Team
```

```text
ID: BACKEND-FIND-03
Area: API Error Contracts
Component: app/routes/downloads.py
Current State: Exceptions in start_download catch generic Exception and return HTTPException(400, detail=str(e)).
Evidence: app/routes/downloads.py lines 38-39 and 99-100.
Requirement: Typed, classified error contracts adhering to RFC 9457 Problem Details.
Problem: Unclassified error strings returned to HTTP clients rather than structured error codes.
User Impact: Client applications must parse unstructured text to determine error causes.
Security Impact: Low (sanitization prevents path leaks).
Reliability Impact: Low.
Performance Impact: None.
Maintainability Impact: Medium.
Root Cause: Standard FastAPI generic exception catching.
Recommended Direction: Map domain exceptions to specific error codes (e.g. INVALID_URL, DOWNLOAD_LIMIT_EXCEEDED).
Implementation Complexity: Low.
Validation Method: Unit tests asserting structured error schemas.
Priority: 🔵 LOW
Owner: Backend API Team
```

---

## 4. Quality Dimension Scorecard

| Dimension | Evaluation | Implementation Detail |
|---|---|---|
| **Domain Logic** | **Strong** | Pure domain functions in `yt_service` and `ffmpeg_service`; queue logic encapsulated in `DownloadQueueManager`. |
| **API Architecture** | **Clean** | Typed Pydantic schemas in `app/engine/protocol.py` for IPC; standard REST schemas in `app/schemas.py`. |
| **Data Access & Storage** | **Optimized** | Single-owner SQLite WAL mode with 500ms write throttling; atomic file promotion (`.part` -> final). |
| **Security Boundaries** | **Hardened** | SSRF pre-DNS resolution, RFC1918 blocking, path traversal containment via `ensure_within_directory`. |
| **External Calls & Timeouts** | **Bounded** | Cancellation tokens (`threading.Event`), network retry with exponential backoff and jitter. |
| **Observability** | **Complete** | Structured JSON logging with automated token masking (`[REDACTED]`), 5MB rotating handler (15MB cap). |
| **Graceful Shutdown** | **Verified** | Stdio EOF triggers clean queue shutdown, active thread cancellation, and database closure. |

---

## 5. Strengths Worth Preserving

1. **Stdio JSON Lines Isolation:** Desktop mode completely avoids opening local network ports, eliminating all localhost loopback attack vectors.
2. **Provider Registry Pattern:** Pluggable source ingestion (`DirectHttpProvider` and universal `YtDlpProvider`) cleanly separates URL matching from downloading.
3. **AST Architectural Fitness Functions:** Automated tests ([`tests/test_architecture_fitness.py`](file:///c:/Users/ASUS/Desktop/STUDY/PROJECTS/yt_dlp_backend/tests/test_architecture_fitness.py)) prevent server frameworks from leaking into core media services.
4. **Resilience & Jittered Backoff:** Transient network resets trigger exponential backoff with jitter (`2^retry + uniform(0.5, 2.0)`), avoiding CDN retry storms.

---

## 6. Prioritized Backend Roadmap

1. **Immediate (Desktop Production):** Maintain the current hardened IPC and queue architecture (all 70 tests passing).
2. **Medium-Term (Server Container Mode):**
   - Add JWT query parameter validation to `app/routes/websockets.py`.
   - Update `docker-compose.yml` to provision a lightweight PostgreSQL service instead of SQLite over Docker volumes.
3. **Long-Term:** Implement RFC 9457 Problem Details for server REST endpoints.
