# MediaDock — Cross-Platform Production Architecture & Support

MediaDock is built from the ground up for native cross-platform deployment across Windows, macOS, and Linux.

## Native OS Matrix & Packaging Targets

| Platform | Target Architecture | Target Triple | Native Bundles | Sidecar Packaging Runner |
|---|---|---|---|---|
| **Windows** | x86_64 (64-bit) | `x86_64-pc-windows-msvc` | NSIS (`.exe`), MSI (`.msi`) | Windows Native Runner (PyInstaller) |
| **macOS** | Apple Silicon (ARM64) | `aarch64-apple-darwin` | Application (`.app`), Disk Image (`.dmg`) | macOS Runner (PyInstaller / codesign) |
| **macOS** | Intel (x86_64) | `x86_64-apple-darwin` | Application (`.app`), Disk Image (`.dmg`) | macOS Runner (PyInstaller / codesign) |
| **Linux** | x86_64 (64-bit) | `x86_64-unknown-linux-gnu` | AppImage, Debian (`.deb`), Red Hat (`.rpm`) | Linux Native Runner (PyInstaller) |

---

## Native Subsystem Details

### 1. File Manager "Reveal in Folder" Integration
- **Windows**: Executes `explorer.exe /select,"<file_path>"` via `std::process::Command`.
- **macOS**: Executes `open -R "<file_path>"`.
- **Linux**: Queries D-Bus `org.freedesktop.FileManager1.ShowItems` with fallback to `xdg-open "<dir_path>"`.

### 2. Audio & Video Toolchain (FFmpeg / FFprobe)
- Binaries are resolved dynamically:
  1. User custom setting configured in Settings pane.
  2. `FFMPEG_PATH` environment variable.
  3. System executable PATH (`where.exe ffmpeg` / `which ffmpeg`).
- If FFmpeg is missing on the host, MediaDock displays diagnostic guidance in the Diagnostics tab rather than crashing.

### 3. IPC Architecture & Process Isolation
- The Python media worker communicates exclusively via standard I/O JSON Lines (`stdin`/`stdout`).
- No local HTTP servers or listening network ports are opened in desktop mode.
- Child worker processes are actively monitored by the Rust supervisor:
  - If the UI window closes, EOF on `stdin` initiates immediate, clean Python sidecar termination.
  - Active downloading threads register cancellation hooks (`threading.Event`) to release file locks promptly.
