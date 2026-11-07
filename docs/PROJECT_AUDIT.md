# MediaDock — Phase 1: Deep Repository Audit Report

**Date:** 2026-11-08  
**Auditor:** Lead Software Architect & Autonomous Engineering Agent  
**Branch Checkpoint:** `chore/phase-1-deep-audit`  
**Working Directory:** `c:\Users\ASUS\Desktop\STUDY\PROJECTS\yt_dlp_backend`

---

## 1. Repositories & Prototypes Identified

### Primary Source of Truth: `yt_dlp_backend`
- **Location:** `c:\Users\ASUS\Desktop\STUDY\PROJECTS\yt_dlp_backend`
- **Git State:** Single historical commit `e0dfa19` ("feat: initialize yt-dlp backend with FastAPI, Celery, Alembic migrations, and Docker Compose orchestration") with multiple uncommitted working modifications.
- **Role:** The primary backend and download engine. All models, migrations, service modules, and configuration originate here.

### Feature Reference Prototype: `YT_DLP`
- **Location:** `C:\Users\ASUS\Desktop\STUDY\PROJECTS\YT_DLP\script.py`
- **Role:** Tkinter/Python prototype providing direct insights into desktop user expectations.
- **Key Features Discovered:**
  - Interactive URL analysis extracting available stream formats (`format_id`, `format_note`, `ext`).
  - Subtitle detection across both author-uploaded `subtitles` and machine-generated `automatic_captions`.
  - Subtitle post-processing with `FFmpegSubtitlesConvertor` targeting `.srt`.
  - User folder selection (`filedialog.askdirectory`) and custom output template construction (`%(title)s.%(ext)s`).

---

## 2. Verification of Historical `PROJECT_AUDIT.md` Claims

The historical `PROJECT_AUDIT.md` contained multiple premature completion claims that had to be verified against the concrete codebase:

| Historical Claim in `PROJECT_AUDIT.md` | Actual Code Verification | Audit Finding |
|---|---|---|
| **Dependency Standardization** ("Verified all project dependencies... listed with pinned versions") | `requirements.txt` has 14 dependencies, but `pytest`, `pytest-asyncio`, `httpx` (for test suite) are completely missing. | **PARTIALLY TRUE** — Runtime packages pinned, but zero test harness or linting tools pinned. |
| **Secret Management** ("Removed hardcoded secrets in `auth.py` to depend securely on configured settings") | `app/config.py` still provides a default fallback `SECRET_KEY = "SET_A_SECURE_SECRET_KEY_IN_ENV"`. Furthermore, `.env` containing sensitive keys was **committed and tracked in Git**. | **FALSE / CRITICAL VULNERABILITY** — Tracked `.env` in Git history. |
| **Database Migration Management** ("Alembic is initialized with complete database models mapped and multiple migration scripts applied") | Verified: 7 migration revisions exist up to `bef9908bb920`. SQLite database `downloads.db` exists with matching columns. However, SQLite `downloads.db` was committed into Git tracking. | **VERIFIED WITH HYGIENE ISSUE** — Migrations work, but database binaries and pycache were committed. |
| **Background Task Broker Connection** ("Refactored celery_app.py to ensure robust broker reconnection routines") | `celery_app.py` has retry settings, but desktop distribution cannot rely on Celery + Redis daemon. | **VERIFIED FOR SERVER, INAPPLICABLE FOR DESKTOP**. |
| **Input & Output Validation** ("Enforced strict Pydantic models across endpoints") | Pydantic models in `schemas.py` are present. However, path traversal vulnerability in `files.py` (`get_file`) allows reading arbitrary system files via unvalidated filename input. | **FALSE / SECURITY GAP** — Severe Path Traversal exists. |
| **Global Exception Handling** ("Global exception hooks cleanly wrap internal server responses preventing trace leakage") | In `app/main.py`, exception handler returns `{"detail": "Internal Server Error", "message": str(exc)}`. Exposing `str(exc)` leaks internal exception messages, database queries, and system paths. | **FALSE / INFORMATION LEAK**. |
| **Health Check Endpoint** ("Exposed /health verifying core environment tool integrations") | Endpoint `/health` verifies `shutil.which('ffmpeg')` and `find_spec('yt_dlp')`. | **VERIFIED** — Functional. |

---

## 3. Security, Vulnerability & Risk Assessment

### 3.1 Critical Vulnerabilities Discovered

1. **Tracked Secrets in Git History (`.env`)**
   - **Severity:** HIGH / CRITICAL
   - **Finding:** `.env` was committed in commit `e0dfa19`.
   - **Remediation Action:**
     - Untracked `.env` from active Git index (`git rm --cached .env`).
     - Generated `.env.example` with non-sensitive placeholder tokens.
     - Updated `.gitignore` to prevent re-committing environment and credential files.
     - *Rotation Requirement:* When deploying to any external or staging environment, all previously committed secrets (`SECRET_KEY`) must be considered compromised and rotated immediately.

2. **Arbitrary File Read / Path Traversal in `/v1/files/{filename}`**
   - **Severity:** HIGH
   - **Finding:** In `app/routes/files.py`:
     ```python
     filepath = os.path.join(str(settings.DOWNLOADS_DIR), filename)
     if not os.path.exists(filepath):
         raise HTTPException(status_code=404, detail="File not found")
     return FileResponse(filepath, filename=filename)
     ```
     An attacker passing `../../../../Windows/win.ini` or sensitive configuration files can read arbitrary host files.
   - **Remediation Action:** Must enforce strict basename validation and path containment within `DOWNLOADS_DIR.resolve()`.

3. **Subprocess & Path Handling in `ffmpeg_service.py`**
   - **Severity:** MEDIUM
   - **Finding:** `subprocess.run(cmd, check=True)` uses list arguments (safe from shell injection), but user-controlled filenames are not checked for existence or non-standard characters, and unquoted title/artist metadata can fail on non-ASCII titles.
   - **Remediation Action:** Validate all input paths before passing to FFmpeg; enforce timeouts and error captures.

4. **SSRF Risk in Webhook Notifications & Download URLs**
   - **Severity:** MEDIUM
   - **Finding:** In `app/worker/tasks.py`: `requests.post(download.webhook_url, json=payload, timeout=5)` allows invoking internal network URLs (e.g. `http://169.254.169.254` or internal LAN services) without host validation.
   - **Remediation Action:** Validate webhook scheme (`http`/`https`) and reject loopback/link-local/private RFC1918 IPs in production environments.

5. **Tracked Binary and Cache Bloat in Git**
   - **Severity:** LOW (Repo Hygiene)
   - **Finding:** `.pyc` files, `downloads.db`, and 3 downloaded test video files (`.mp4`, ~12MB) were committed to Git.
   - **Remediation Action:** Added proper rules to `.gitignore` and removed tracked entries from Git staging index.

---

## 4. Reusable Modules vs Obsolete / Mocked Implementations

| Module / Component | Current Implementation State | Reusability in MediaDock | Recommended Action |
|---|---|---|---|
| `app/services/yt_service.py` | Functional `yt-dlp` wrapper for metadata & downloading. | **HIGH (Core Engine)** | **REFACTOR:** Decouple from SQLAlchemy/Celery; expose pure functional metadata parsing, format selection, and progress hooks for JSONL IPC. |
| `app/services/ffmpeg_service.py` | Audio conversion, re-encoding, and metadata embedding. | **HIGH** | **REFACTOR:** Add FFmpeg binary auto-detection (bundled vs system vs user-specified), robust error handling, and progress parsing. |
| `app/models.py` & `alembic/` | SQLite models for `Download`, `User` with migration history. | **HIGH** | **RETAIN:** Maintain compatibility for desktop database storage. |
| `app/services/ai_service.py` | Stubbed mock returning static strings. | **LOW / MOCK** | **REPLACE:** Replace with genuine optional Gemini / local summarization if requested, or isolate as an optional plugin. |
| `app/services/storage_service.py` | Stubbed mock for S3 upload. | **LOW / MOCK** | **REMOVE / ISOLATE:** S3 upload is not relevant for local desktop downloader. Keep local storage provider only. |
| `app/worker/celery_app.py` & `tasks.py` | Celery + Redis asynchronous tasks. | **MEDIUM (Server only)** | **RETAIN FOR SERVER, REPLACE FOR DESKTOP:** For desktop runtime, provide Rust Tokio task queue; keep celery modules uncorrupted for server deployment mode. |
| `app/routes/a.py` | Single line junk file (`print("Hello worlld!")`). | **NONE** | **REMOVE:** Obsolete scratch file. |
| `fix.py` | Temporary rename script for `db.py` -> `database.py`. | **NONE** | **REMOVE / ARCHIVE:** Obsolete one-off scratch script. |

---

## 5. Dependency Topology & Ecosystem Coupling

```
[ FastAPI Endpoints ] 
       │
       ├──> [ SQLAlchemy Models & SQLite Engine ]
       │
       ├──> [ Celery Worker Tasks ] ──> [ Redis Broker & PubSub ]
       │           │
       │           └──> [ yt_service (yt-dlp) ] ──> [ FFmpeg CLI ]
       │           │
       │           └──> [ ai_service (Mock) ]
       │
       └──> [ ffmpeg_service ] ──> [ FFmpeg CLI ]
```

### Decoupling Strategy for MediaDock Desktop:
In Tauri 2 desktop mode:
- The UI communicates directly with the Tauri Rust Core via Tauri IPC.
- Rust Core manages the download queue, SQLite persistence, and spawns the Python sidecar process.
- The Python sidecar directly imports `yt_service` and `ffmpeg_service` without booting FastAPI, Celery, or Redis.
- The FastAPI, Celery, and WebSocket routes remain intact for headless/server deployment workflows.
