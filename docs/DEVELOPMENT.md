# MediaDock — Local Development Guide

## Prerequisites
- **Python**: 3.11+ (Python 3.13 recommended)
- **Rust**: 1.80+ (via rustup)
- **Node.js**: 20+ (with npm)
- **FFmpeg & FFprobe**: Installed and available on system PATH

---

## 1. Python Engine Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pyinstaller
```

### Running Python Tests
```bash
pytest -v tests/
```

---

## 2. Frontend Development

```bash
cd frontend

# Install packages
npm install

# Run unit & component tests
npm test

# Run code linter
npm run lint

# Start development dev server
npm run dev

# Build production bundle
npm run build
```

---

## 3. Desktop Application (Tauri 2)

```bash
# Package sidecar binary for target triple (e.g. Windows)
pyinstaller packaging/sidecar.spec --noconfirm
mkdir -p src-tauri/binaries
cp dist/mediadock-sidecar.exe src-tauri/binaries/mediadock-sidecar-x86_64-pc-windows-msvc.exe

# Run Rust tests
cd src-tauri
cargo fmt --check
cargo clippy -- -D warnings
cargo test

# Run desktop app in development mode
cargo tauri dev
```
