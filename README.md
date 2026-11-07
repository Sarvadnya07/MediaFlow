# MediaDock

> **A high-performance, secure, cross-platform desktop media management suite powered by Tauri 2, React, TypeScript, and yt-dlp.**

[![CI Release Matrix](https://github.com/mediadock/mediadock/actions/workflows/build.yml/badge.svg)](https://github.com/mediadock/mediadock/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Overview

MediaDock upgrades existing download backends into a production-grade native desktop application for **Windows**, **macOS**, and **Linux**.

Combining a lightweight **Rust (Tauri 2)** desktop shell with an optimized **Python (yt-dlp)** media engine over structured **stdio JSON Lines IPC**, MediaDock delivers fast, secure, and reliable media downloading and audio transcoding with zero unauthenticated local network exposure.

---

## Key Features

- ⚡ **Native Performance**: Ultra-low memory footprint using Tauri 2 and modern React 19.
- 🔒 **Comprehensive Security**: Full SSRF protection, DNS rebinding guards, private IP blocking, path traversal defenses, and strict Content Security Policy (CSP).
- 📦 **Zero-Config Queue**: Persistent SQLite-backed download queue with auto-recovery on restart, cancellation hooks, and concurrency limits.
- 🎵 **Advanced Audio Transcoding**: Automatic conversion to MP3, M4A, AAC, FLAC, WAV, Opus, and OGG using native FFmpeg.
- 📊 **Real-Time Diagnostics**: Live sidecar health check, yt-dlp version reporting, and FFmpeg audio/video encoder discovery.
- 📁 **Native OS Integration**: "Reveal in Folder" support for Windows Explorer, macOS Finder, and Linux file managers.

---

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Local Development Guide](docs/DEVELOPMENT.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Cross-Platform Details](docs/CROSS_PLATFORM.md)
- [Security Model & Threat Mitigation](docs/SECURITY.md)
- [Legal Compliance & Fair Use Notice](docs/LEGAL.md)
- [Third-Party Licenses](docs/THIRD_PARTY_LICENSES.md)
- [Changelog](CHANGELOG.md)

---

## License

MediaDock is open-source software licensed under the [MIT License](LICENSE).
