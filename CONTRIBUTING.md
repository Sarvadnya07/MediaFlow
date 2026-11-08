# Contributing to MediaFlow

Thank you for your interest in contributing to **MediaFlow**! We welcome bug reports, feature enhancements, documentation improvements, and architectural reviews.

---

## 1. Code of Conduct

All contributors and maintainers are expected to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please ensure interactions remain professional, constructive, and respectful.

---

## 2. Development Setup

MediaFlow is a dual-topology application:
1. **Desktop Client:** Tauri 2 (Rust) + React 19 / TypeScript + Python yt-dlp Sidecar.
2. **Headless Engine:** FastAPI + Celery + Redis + PostgreSQL/SQLite.

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 20+ (LTS) & npm
- **Rust Toolchain**: 1.78+ (via rustup)
- **FFmpeg**: Ensure `ffmpeg` and `ffprobe` are installed on your system PATH.

### Installation Steps
```bash
# 1. Clone repository
git clone https://github.com/your-username/mediaflow.git
cd mediaflow

# 2. Setup Python environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements-dev.txt

# 3. Setup Frontend
cd frontend
npm install
cd ..
```

---

## 3. Pull Request Guidelines

1. **Least-Privilege Security Principles**: Never bypass URL validation, SSRF checks, or filesystem containment rules.
2. **Deterministic Verification**: Every modification must include automated tests or maintain 100% pass rates across the test suites:
   - **Python Tests**:
     ```bash
     pytest -q -m "not network" tests/
     ```
   - **Frontend Tests**:
     ```bash
     cd frontend && npx vitest run
     ```
   - **Rust Tauri Tests**:
     ```bash
     cargo test --lib --manifest-path src-tauri/Cargo.toml
     ```
3. **Linting & Formatting**:
   - Python: format with `black` and lint with `flake8`.
   - Frontend: `npm run lint`.
   - Rust: `cargo fmt --check` and `cargo clippy`.
4. **Target Branch**: Submit all pull requests against the `main` (or `master`) branch with clear, descriptive titles and reproduction/verification logs.
5. **No Tracked Transient Artifacts**: Ensure no `.db`, `.log`, `.env`, or build artifacts are accidentally staged.
