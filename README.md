# 🚀 YT-DLP Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![Celery](https://img.shields.io/badge/celery-%2337814A.svg?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

A high-performance, asynchronous backend service for downloading and converting video/audio content from YouTube and 1000+ other sites. Built with **FastAPI**, **Celery**, and **yt-dlp**, this service provides a robust API to manage media downloads, format conversions, and file organization.

---

## ✨ Features

- **Asynchronous Processing**: Uses Celery workers to handle heavy download and conversion tasks in the background.
- **Universal Compatibility**: Powered by `yt-dlp`, supporting thousands of video hosting platforms.
- **Media Conversion**: Integrated FFmpeg support for seamless MP4/MP3 conversions and quality adjustments.
- **Secure Authentication**: JWT-based authentication system with user management.
- **Task Management**: Track download status, retries, and file history via a centralized database.
- **Storage Management**: Automated file organization and clean-up utilities.
- **Modern API**: Auto-generated Swagger and Redoc documentation.

---

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Task Queue**: [Celery](https://docs.celeryq.dev/) with [Redis](https://redis.io/)
- **Database**: [SQLAlchemy](https://www.sqlalchemy.org/) (SQLite for portability, PostgreSQL ready)
- **Engine**: [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Processing**: [FFmpeg](https://ffmpeg.org/)
- **Security**: [Jose (JWT)](https://python-jose.readthedocs.io/), [Passlib (Bcrypt)](https://passlib.readthedocs.io/)

---

## 🏗️ Architecture

The system follows a decoupled architecture to ensure scalability and reliability:

1. **API Gateway (FastAPI)**: Handles incoming requests, authentication, and task dispatching.
2. **Worker Engine (Celery)**: Consumes tasks from the Redis queue and executes `yt-dlp`/`ffmpeg` commands.
3. **Storage Layer**: Persists metadata in SQLite/PostgreSQL and stores media files in a structured local directory.
4. **Message Broker (Redis)**: Orchestrates communication between the API and Workers.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) (must be in system PATH)
- [Redis](https://redis.io/download) (for Celery broker)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/yt-dlp-backend.git
   cd yt-dlp-backend
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_super_secret_key
   DATABASE_URL=sqlite:///./downloads.db
   REDIS_URL=redis://localhost:6379/0
   ```

### 🐳 Docker Deployment (Recommended)

The easiest way to run the entire stack (API, Worker, Redis) is using Docker Compose:

1. **Build and start services:**
   ```bash
   docker-compose up --build -d
   ```

2. **Run migrations (inside container):**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

The API will be available at `http://localhost:8000`.

---

## 📖 Usage

### 1. Start the API Server
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`. Access `/docs` for the interactive Swagger UI.

### 2. Start the Celery Worker
```bash
celery -A app.worker.celery_app worker --loglevel=info
```

### 3. Example Request (Download Video)
```bash
curl -X 'POST' \
  'http://localhost:8000/v1/downloads/' \
  -H 'Authorization: Bearer <your_token>' \
  -H 'Content-Type: application/json' \
  -d '{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "bestvideo+bestaudio/best",
  "ext": "mp4"
}'
```

---

## 📂 Folder Structure

```text
.
├── app/
│   ├── routes/          # API Endpoints (Auth, Downloads, Files)
│   ├── services/        # Core Logic (yt-dlp, ffmpeg wrappers)
│   ├── worker/          # Celery app and task definitions
│   ├── models.py        # SQLAlchemy Database Models
│   ├── schemas.py       # Pydantic Validation Schemas
│   ├── auth.py          # Security and JWT Logic
│   └── database.py      # DB Connection & Session Management
├── downloads/           # Default directory for downloaded media
├── requirements.txt     # Project dependencies
└── .env.example         # Template for environment variables
```

---

## 🔒 Security Considerations

- **JWT Expiration**: Access tokens are short-lived. Refresh token logic is recommended for production.
- **Path Traversal**: Input URLs and filenames are sanitized to prevent unauthorized file system access.
- **Rate Limiting**: It is highly recommended to put this behind a reverse proxy (Nginx) with rate limiting enabled.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 👤 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your Name](https://linkedin.com/in/yourname)

---

> [!TIP]
> Always ensure `yt-dlp` is updated to the latest version to maintain compatibility with platform changes: `pip install -U yt-dlp`.
