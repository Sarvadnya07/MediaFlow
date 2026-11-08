# MediaFlow — Installation & Setup Guide

MediaFlow can be deployed either as a **Desktop Application** or as a **Headless API & Worker Backend**. Choose the installation instructions below matching your target environment.

---

## 1. System Prerequisites

Before beginning, ensure your system meets the minimum requirements:

| Dependency | Minimum Version | Required By | Installation Reference |
| :--- | :--- | :--- | :--- |
| **Python** | 3.11+ | Media Engine & API | [python.org](https://www.python.org/) |
| **FFmpeg** | 4.4+ (6.0+ recommended) | Remuxing & Transcoding | [ffmpeg.org](https://ffmpeg.org/) |
| **Node.js** | 20+ LTS | Desktop UI | [nodejs.org](https://nodejs.org/) |
| **Rust** | 1.78+ | Tauri Supervisor | [rustup.rs](https://rustup.rs/) |
| **Docker** | 24.0+ *(Optional)* | Containerized Headless Stack | [docker.com](https://www.docker.com/) |

> [!IMPORTANT]
> Verify that `ffmpeg` and `ffprobe` are executable from your terminal by running:
> ```bash
> ffmpeg -version
> ffprobe -version
> ```

---

## 2. Desktop Application Setup (Development Mode)

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/mediaflow.git
cd mediaflow
```

### Step 2: Python Virtual Environment
```bash
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Step 3: Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### Step 4: Run Desktop in Development
```bash
# In frontend directory:
cd frontend
npm run tauri dev
```
Tauri will compile the Rust supervisor, initialize the Python background sidecar over standard I/O, and launch the React UI window.

---

## 3. Headless Server & Docker Setup

### Step 1: Environment Configuration
Copy the configuration template to `.env`:
```bash
cp .env.example .env
```
Open `.env` and verify the parameters.

### Step 2: Launch with Docker Compose
```bash
docker compose up -d --build
```
This launches:
- `mediaflow-db`: PostgreSQL 16
- `mediaflow-redis`: Redis 7 Broker
- `mediaflow-api`: FastAPI backend with Alembic migrations on port `8000`
- `mediaflow-worker`: Celery worker dedicated to download & processing queues

Verify running containers:
```bash
docker compose ps
```

Visit the interactive OpenAPI documentation at: `http://localhost:8000/docs`.

---

## 4. Troubleshooting Common Setup Issues

### `ffmpeg: command not found`
- **Linux**: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo dnf install ffmpeg` (Fedora).
- **macOS**: `brew install ffmpeg`
- **Windows**: Install via `winget install Gyan.FFmpeg` or extract binaries and append to System `PATH`.

### SQLite Database Locked in Desktop Mode
Ensure no orphan Python sidecar processes are running in Task Manager. MediaFlow uses WAL mode to prevent locking during normal operations.
