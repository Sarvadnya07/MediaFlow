# Changelog

All notable changes to MediaDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-08

### Added
- **Native Desktop Shell**: Tauri 2 application foundation with React 19, TypeScript, and Vite.
- **Python Sidecar IPC Engine**: High-performance stdio JSON Lines bidirectional IPC supervisor.
- **Core Downloader UI**: URL analysis, dynamic media stream selection (resolution, frame rate, audio-only extraction), and estimated file size display.
- **Advanced Queue Management**: SQLite-backed persistent download manager with crash recovery, configurable concurrency, and write throttling.
- **Audio & Media Processing**: FFmpeg binary discovery, encoder detection, and atomic transcoding for MP3, M4A, AAC, FLAC, WAV, Opus, and OGG.
- **Security Hardening**: Strict SSRF defenses, private IP blocking, DNS rebinding checks, filename sanitization, path traversal containment, and Webview CSP.
- **Cross-Platform Release Pipelines**: Native packaging specifications and GitHub Actions CI matrix for Windows (NSIS, MSI), macOS (DMG, App), and Linux (AppImage, DEB, RPM).
- **Automated Test Matrix**: 28 pytest suite tests, 3 Rust cargo tests, and frontend Vitest component tests.
