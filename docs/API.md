# MediaFlow — REST & WebSocket API Specification

When running MediaFlow in **Headless Server Mode** (`uvicorn app.main:app` or `docker compose up`), the service provides a RESTful API and WebSocket real-time progress stream.

Interactive OpenAPI documentation is accessible at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 1. Authentication & Tokens

Protected endpoints require a Bearer token in the `Authorization` HTTP header:
```http
Authorization: Bearer <your_jwt_token>
```

### POST `/api/v1/auth/token`
Obtain a JWT access token using form credentials.
- **Request (application/x-www-form-urlencoded)**:
  - `username`: string
  - `password`: string
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

---

## 2. Media Extraction & Information

### POST `/api/v1/extract`
Analyze a media URL to extract title, duration, thumbnail, available video formats, audio streams, and chapters.

- **Request (application/json)**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
    "uploader": "Rick Astley",
    "duration": 213,
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    "extractor": "youtube",
    "formats": [
      {
        "format_id": "137",
        "resolution": "1080p",
        "ext": "mp4",
        "fps": 30,
        "filesize": 45120100
      },
      {
        "format_id": "140",
        "resolution": "audio only",
        "ext": "m4a",
        "abr": 128
      }
    ]
  }
  ```

---

## 3. Downloads & Task Management

### POST `/api/v1/download`
Submit a new download request to the Celery worker queue.

- **Request (application/json)**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format_id": "137+140",
    "audio_only": false,
    "extract_audio_format": "mp3"
  }
  ```
- **Response (202 Accepted)**:
  ```json
  {
    "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "queued",
    "message": "Download task enqueued successfully."
  }
  ```

### GET `/api/v1/status/{task_id}`
Query download task status, download percentage, speed, and completed file path.

- **Response (200 OK)**:
  ```json
  {
    "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "downloading",
    "progress": 64.2,
    "speed": "2.4 MB/s",
    "eta": "00:15",
    "filename": "Rick_Astley_Never_Gonna_Give_You_Up.mp4"
  }
  ```

---

## 4. Real-Time WebSocket Progress

### WebSocket `/ws/downloads`
Connect to receive real-time JSON event packets as download workers report progress.

- **Event Payload Example**:
  ```json
  {
    "event": "progress",
    "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "downloaded_bytes": 14200000,
    "total_bytes": 22100000,
    "percent": 64.2,
    "speed": 2516582,
    "eta": 15
  }
  ```
