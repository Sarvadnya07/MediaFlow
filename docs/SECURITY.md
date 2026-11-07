# MediaDock — Security Architecture & Threat Model

## 1. Core Principles
- **No DRM Circumvention**: MediaDock strictly processes unencrypted, publicly accessible media streams supported natively by yt-dlp. It does not tamper with or bypass Widevine, FairPlay, or PlayReady DRM systems.
- **No Cookie Harvesting**: MediaDock does not extract or copy session cookies or browser credentials without explicit, intentional user configuration.
- **Zero Local Network Exposure**: Desktop mode operates over standard I/O (stdio JSON Lines). It opens zero listening TCP sockets or unauthenticated local web servers.

---

## 2. Implemented Defenses

### SSRF (Server-Side Request Forgery) & DNS Rebinding
- Handled in `app/security.py`:
  - Disallows non-HTTP/HTTPS schemes (e.g. `file://`, `gopher://`, `ftp://`).
  - Blocks embedded credentials in URLs (`user:pass@host`).
  - Blocks loopback targets (`localhost`, `127.0.0.1`, `::1`).
  - Performs DNS resolution before dispatch to ensure domain names do not resolve to RFC1918 private IPv4 addresses (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local IPs, or multicast ranges.

### Path Traversal & Filesystem Containment
- Filename sanitization (`sanitize_filename`):
  - Strips path traversal sequences (`../`, `..\`) and illegal characters (`*?:"<>|`).
  - Enforces string truncation to prevent filesystem buffer overflow.
- Directory containment (`ensure_within_directory`):
  - Resolves target paths and validates that `resolved_target.relative_to(base_dir)` holds true before write or conversion actions.

### Subprocess Execution
- Subprocess invocations (FFmpeg, FFprobe, and PyInstaller sidecar) use structured argument lists (`exec` format) rather than raw shell command strings (`shell=False`).
- Custom user-configured binary paths are explicitly verified for existence and executable permissions before invocation.

### Webview Content Security Policy (CSP)
- MediaDock strictly enforces CSP in Tauri webviews:
  ```
  default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https: asset: http://asset.localhost; font-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost
  ```

---

## 3. Reporting Security Vulnerabilities
If you discover a security vulnerability in MediaDock, please report it privately via GitHub Security Advisories or email the maintainers directly. Do not report security vulnerabilities in public issue trackers.
