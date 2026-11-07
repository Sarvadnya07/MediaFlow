# MediaDock — Test & Verification Report

## Baseline Verification (2026-11-08)

### 1. Toolchain & Environment Audit
| Tool | Expected | Detected Version | Status |
|---|---|---|---|
| Python | 3.10+ | 3.12.10 | PASS |
| Node.js | 18+ | 26.2.0 | PASS |
| npm | 9+ | 12.0.2 | PASS |
| FFmpeg | 5.0+ | 7.1-full_build-www.gyan.dev | PASS |
| Rust / Cargo | 1.70+ | cargo 1.97.1 (stable MSVC) | PASS (via toolchain path) |

### 2. Existing Python Engine Validation
- Verified `requirements.txt` includes: `yt-dlp>=2025.02.19`, `fastapi`, `sqlalchemy`, `pydantic`.
- Verified feature set from historical Tkinter prototype (`YT_DLP/script.py`):
  - Resolution & format ID listing.
  - Subtitle detection (`subtitles` and `automatic_captions`).
  - FFmpegSubtitlesConvertor (SRT conversion).
  - Outtmpl configuration and progress hooks.

### 3. Test Suites
- [ ] Python unit & integration tests (`pytest`)
- [ ] Sidecar JSONL protocol test suite
- [ ] Frontend test suite (`vitest`)
- [ ] Rust core unit tests (`cargo test`)
