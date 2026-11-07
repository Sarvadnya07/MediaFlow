# Contributing to MediaDock

Thank you for your interest in contributing to MediaDock!

## Code of Conduct
Please be polite, constructive, and respectful to all maintainers and contributors.

## Pull Request Guidelines
1. Ensure all changes adhere to least-privilege security principles.
2. Every new feature or bug fix must include corresponding tests:
   - Python media engine: `pytest`
   - Rust supervisor: `cargo test`
   - Frontend components: `vitest`
3. Verify that all linters and formatters pass:
   - `cargo fmt --check`
   - `cargo clippy -- -D warnings`
   - `npm run lint`
   - `npm test`
4. Update governance artifacts when altering interfaces (`docs/ARCHITECTURE.md`, `BUILD_STATUS.md`).
5. Open PRs against `master` with descriptive titles and verification logs.
