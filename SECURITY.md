# MediaFlow — Security Policy & Threat Model

## 1. Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## 2. Core Security Principles

- **Zero DRM Circumvention**: MediaFlow strictly processes unencrypted, publicly accessible media streams supported natively by yt-dlp. It does not tamper with, decrypt, or bypass Widevine, FairPlay, or PlayReady DRM systems.
- **No Cookie Harvesting**: MediaFlow does not extract, exfiltrate, or copy session cookies or browser credentials without explicit, intentional user configuration.
- **Zero Local Network Exposure in Desktop Mode**: Desktop mode operates over standard I/O (stdio JSON Lines). It opens zero listening TCP sockets or unauthenticated local web servers.
- **Strict Network Boundary Controls**: Headless/API modes validate and filter all user-provided URLs prior to external dispatch.

---

## 3. Threat Model & Implemented Mitigations

### Server-Side Request Forgery (SSRF) & DNS Rebinding
MediaFlow incorporates multi-layered URL inspection in `app/security.py`:
- **Protocol Allowlist**: Only `http://` and `https://` schemes are permitted; protocols such as `file://`, `gopher://`, and `ftp://` are rejected.
- **Credential Stripping**: Reject URLs containing embedded credentials (`user:pass@host`).
- **Loopback & Private Address Blocking**: Blocks `localhost`, `127.0.0.1`, `::1`.
- **Pre-dispatch DNS Resolution**: Domain names are resolved prior to dispatch to prevent DNS rebinding attacks targeting private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), RFC 3927 link-local addresses, or cloud metadata endpoints (`169.254.169.254`).

### Path Traversal & Filesystem Containment
- **Filename Sanitization**: Replaces path traversal sequences (`../`, `..\`) and reserved OS filesystem characters (`*?:"<>|`).
- **Directory Containment**: All target paths are canonically resolved and verified to reside strictly within `DOWNLOADS_DIR` before file creation, mutation, or deletion.

### Subprocess Security
- Subprocess invocations (FFmpeg, FFprobe, and PyInstaller sidecar) use structured argument lists (`exec` format) with `shell=False`.
- Custom user-configured binary paths are strictly verified for filesystem existence and executable permissions before invocation.

### Webview Content Security Policy (CSP)
In Desktop mode, Tauri enforces a strict Content Security Policy:
```text
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https: asset: http://asset.localhost; font-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost
```

---

## 4. Reporting Security Vulnerabilities

If you discover a security vulnerability or security bug in MediaFlow, **please do not disclose it publicly** via GitHub Issues or public channels.

Instead, please report it via:
1. **GitHub Private Security Advisory**: Use the "Report a vulnerability" button on the repository Security tab.
2. **Direct Maintainer Contact**: Email the security response team at `security@mediaflow.local` with detailed reproduction steps, proof-of-concept, and impact assessment.

We acknowledge reports within 48 hours and coordinate public disclosure timelines following mitigation.
