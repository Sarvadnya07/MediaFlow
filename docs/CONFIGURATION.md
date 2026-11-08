# MediaFlow — Configuration Reference

MediaFlow configuration is managed through environment variables, backed by Pydantic's `BaseSettings` (`app/config.py`).

---

## 1. Environment Variable Reference

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | string | `"MediaFlow"` | Application display name in logs and Swagger docs. |
| `DEBUG` | boolean | `False` | Enables verbose tracebacks and reload triggers. **Disable in production.** |
| `ENVIRONMENT` | string | `"development"` | Active runtime mode (`development`, `staging`, `production`). |
| `LOG_LEVEL` | string | `"INFO"` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `SECRET_KEY` | string | *(Required in prod)* | High-entropy secret string used for signing JWTs and session tokens. |
| `ALGORITHM` | string | `"HS256"` | JWT token hashing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| integer | `60` | JWT expiration duration in minutes. |
| `RATE_LIMIT_PER_MINUTE` | integer | `60` | Maximum API requests allowed per client IP per minute. |
| `DATABASE_URL` | string | `sqlite:///./downloads.db` | SQLAlchemy connection URI (supports SQLite and PostgreSQL). |
| `REDIS_URL` | string | `redis://localhost:6379/0` | Connection URI for Celery message broker and caching. |
| `CELERY_BROKER_URL` | string | `redis://localhost:6379/0` | Explicit Celery broker URI override. |
| `CELERY_RESULT_BACKEND` | string | `redis://localhost:6379/0` | Celery result storage URI. |
| `DOWNLOADS_DIR` | path | `downloads` | Filesystem directory where downloaded media and temporary files reside. |
| `MAX_CONCURRENT_DOWNLOADS` | integer | `3` | Maximum active simultaneous downloads in queue coordinator. |
| `USE_S3` | boolean | `False` | When `True`, offloads completed downloads to an S3 bucket. |
| `S3_BUCKET` | string | `"my-mediaflow-bucket"` | AWS S3 target bucket name. |
| `S3_REGION` | string | `"us-east-1"` | AWS S3 target region. |
| `FFMPEG_PATH` | string | System PATH | Explicit override path to the `ffmpeg` executable. |
| `FFPROBE_PATH` | string | System PATH | Explicit override path to the `ffprobe` executable. |

---

## 2. Desktop Mode Settings Persistence

In Desktop mode, user settings (such as chosen download path, audio-only extraction defaults, notifications, and clipboard monitoring) are persisted in the desktop browser sandbox via `localStorage`.

When launching the desktop application:
- `mediaflow_settings_v1`: JSON object storing client preferences.
- SQLite WAL databases (`mediadock_queue.db`, `mediadock_library.db`) store media library indices and task states across restarts.

---

## 3. Database Migration Management

Alembic tracks database schema revisions for PostgreSQL and SQLite server modes.

```bash
# Apply pending schema migrations
alembic upgrade head

# Create a new revision after updating app/models/
alembic revision --autogenerate -m "describe_migration"

# Revert previous migration
alembic downgrade -1
```
