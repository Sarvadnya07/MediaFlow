## Summary of Changes
<!-- A clear and concise description of what this PR does and why it was introduced. -->

## Motivation & Context
<!-- Reference related issue(s) using #issue_id, or explain background context. -->

## Changes Checklist
- [ ] Backend Python changes (FastAPI / Celery / yt-dlp)
- [ ] Desktop Tauri / Rust supervisor changes
- [ ] Frontend React / TypeScript UI changes
- [ ] Documentation, schema, or configuration updates

## Verification & Testing
<!-- Describe how these changes were tested and paste output evidence. -->
- **Offline Pytest**: `pytest -q -m "not network" tests/`
- **Frontend Vitest**: `cd frontend && npx vitest run`
- **Rust Cargo**: `cargo test --lib --manifest-path src-tauri/Cargo.toml`
- **Linter / Formatter**: `black --check .` / `flake8` / `npm run lint`

## Security & Boundary Checks
- [ ] No hardcoded secrets, API tokens, or session credentials.
- [ ] URL validation and SSRF guards maintained.
- [ ] File operations remain bounded within `DOWNLOADS_DIR`.
- [ ] No transient files (`.db`, `.log`, `.env`) committed.
