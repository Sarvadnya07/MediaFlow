# MediaDock — Known Limitations & Risk Registry

## 1. Environment & Platform Dependencies
- **Rust Toolchain Shim on Windows:** The local environment has Rust toolchain components in `C:\Users\ASUS\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin`. Direct symlinks in `.cargo\bin` point to missing rustup shim, requiring invocation via toolchain bin directory or proper environment PATH mapping.
- **FFmpeg Requirement:** Certain advanced operations (merging separate video/audio streams, embedding soft subtitles, transcode to MP3) require FFmpeg. An alert and settings fallback must be surfaced to users if FFmpeg is missing from PATH.

## 2. Platform Access Restrictions & Policy Bounds
- **DRM and Encrypted Streams:** MediaDock strictly refuses and cannot download DRM-protected content (Widevine, FairPlay, PlayReady), encrypted HLS keys, or paid subscriber-only videos.
- **Paywalls & Authentication:** No browser cookie scraping, credential harvesting, or authentication bypass mechanisms are supported.
- **Rate Limiting & Anti-bot Measures:** Target platforms may issue temporary HTTP 429 or CAPTCHA challenges if too many concurrent connections are established.

## 3. Storage & Concurrency
- **Disk Space Allocation:** High-definition video downloads (e.g. 4K 60fps) require temporary storage for both video and audio streams prior to FFmpeg muxing, needing at least 2.5x the final file size in free temporary disk space.
- **Cancellation Latency:** While Python process cancellation can interrupt downloads quickly, ongoing FFmpeg muxing steps must be terminated cleanly without leaving corrupt temporary artifacts.
