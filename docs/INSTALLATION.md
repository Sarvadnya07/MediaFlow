# MediaDock — Installation Guide

MediaDock can be run either as a native desktop application or as a headless server backend.

---

## 1. Desktop Application Installation

### Windows
1. Download `MediaDock-Setup-x64.exe` (NSIS) or `MediaDock-x64.msi` from the [Releases](https://github.com/mediadock/mediadock/releases) page.
2. Run the installer and follow the setup wizard.
3. Launch **MediaDock** from the Start Menu.

### macOS
1. Download `MediaDock-Universal.dmg` or architecture-specific DMG (`aarch64` for Apple Silicon, `x64` for Intel).
2. Open the DMG and drag **MediaDock.app** into `/Applications`.
3. Launch MediaDock from Finder or Spotlight.

### Linux
1. **AppImage**:
   ```bash
   chmod +x MediaDock-x86_64.AppImage
   ./MediaDock-x86_64.AppImage
   ```
2. **Debian / Ubuntu (`.deb`)**:
   ```bash
   sudo dpkg -i mediadock_amd64.deb
   sudo apt-get install -f
   ```
3. **Fedora / RHEL (`.rpm`)**:
   ```bash
   sudo rpm -ivh mediadock_x86_64.rpm
   ```

---

## 2. Headless Server Mode (Optional)

If running MediaDock in cloud / Docker mode:

```bash
# Clone the repository
git clone https://github.com/mediadock/mediadock.git
cd mediadock

# Copy and configure environment variables
cp .env.example .env

# Launch with Docker Compose
docker compose up -d
```
