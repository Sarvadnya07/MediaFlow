"""
Direct HTTP / Generic Media Provider.
Handles direct audio/video web links (e.g. mp4, webm, mp3, m4a, flac, wav, ogg) over HTTP/HTTPS.
"""
import os
import re
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Callable, Dict, Optional

from app.providers.base import BaseProvider, ProviderInfo, ProviderCapability
from app.engine.protocol import MediaAnalysisResult, MediaFormatInfo
from app.security import validate_and_sanitize_url, sanitize_filename, ensure_within_directory
from app.config import settings
from app.services.yt_service import DownloadCancelledError, _active_cancellations, _cancellation_lock


class DirectHttpProvider(BaseProvider):
    DIRECT_EXTENSIONS = {
        ".mp4", ".mkv", ".webm", ".avi", ".mov",
        ".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus"
    }

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="direct_http",
            name="Direct Web Media (HTTP/S)",
            description="Direct media file streams and static web URLs (.mp4, .mp3, .webm, .wav, etc.)",
            version="1.0.0",
            homepage="https://developer.mozilla.org/en-US/docs/Web/HTTP",
            supported_domains=["*"],
            capabilities=ProviderCapability(
                video=True,
                audio=True,
                playlists=False,
                subtitles=False,
                metadata=True,
                chapters=False,
                thumbnails=False,
            ),
            status="active",
            requires_auth=False,
            notes="Processes direct audio/video file downloads without scraper overhead."
        )

    def matches_url(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url.strip())
        path = parsed.path.lower()
        return any(path.endswith(ext) for ext in self.DIRECT_EXTENSIONS)

    def analyze(self, url: str, allow_private: bool = False) -> MediaAnalysisResult:
        safe_url = validate_and_sanitize_url(url, allow_private=allow_private)
        parsed = urlparse(safe_url)
        path = parsed.path
        filename = Path(path).name or "direct_media"
        ext = Path(path).suffix.lower().lstrip(".") or "mp4"

        is_audio = ext in {"mp3", "m4a", "aac", "flac", "wav", "ogg", "opus"}

        content_length = None
        try:
            resp = requests.head(safe_url, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                cl = resp.headers.get("content-length")
                if cl and cl.isdigit():
                    content_length = int(cl)
        except Exception:
            pass

        format_info = MediaFormatInfo(
            format_id="direct_stream",
            ext=ext,
            resolution="source" if not is_audio else None,
            filesize=content_length,
            vcodec=None if is_audio else "source",
            acodec="source",
            fps=None,
            abr=None,
            format_note="Direct File Stream",
        )

        return MediaAnalysisResult(
            url=safe_url,
            extractor="direct_http",
            id=re.sub(r'[^a-zA-Z0-9_-]', '_', filename),
            title=Path(filename).stem,
            description="Direct HTTP/S media resource",
            duration=None,
            uploader=parsed.netloc,
            thumbnail=None,
            formats=[format_info],
            subtitles=[],
            automatic_captions=[],
            is_playlist=False,
        )

    def download(
        self,
        url: str,
        format_id: Optional[str] = None,
        output_dir: Optional[str] = None,
        output_template: Optional[str] = None,
        subtitle_lang: Optional[str] = None,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
        job_id: Optional[str] = None,
        allow_private: bool = False,
    ) -> Dict[str, Any]:
        safe_url = validate_and_sanitize_url(url, allow_private=allow_private)
        base_dir = Path(output_dir or settings.DOWNLOAD_DIR).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)

        parsed = urlparse(safe_url)
        filename = sanitize_filename(Path(parsed.path).name or "downloaded_media.mp4")
        target_path = ensure_within_directory(base_dir / filename, base_dir)

        # Check cancellation
        def check_cancelled():
            if job_id:
                with _cancellation_lock:
                    token = _active_cancellations.get(job_id)
                    if token and token.is_set():
                        raise DownloadCancelledError(f"Job {job_id} was cancelled by user.")

        check_cancelled()

        resp = requests.get(safe_url, stream=True, timeout=15)
        resp.raise_for_status()

        total_bytes = int(resp.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.time()
        last_progress_time = 0.0

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                check_cancelled()
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    if progress_hook and (now - last_progress_time >= 0.5 or (total_bytes and downloaded == total_bytes)):
                        last_progress_time = now
                        elapsed = max(now - start_time, 0.001)
                        speed = downloaded / elapsed
                        eta = int((total_bytes - downloaded) / speed) if total_bytes and speed > 0 else None
                        percent = (downloaded / total_bytes * 100.0) if total_bytes else 0.0

                        progress_hook({
                            "status": "downloading",
                            "downloaded_bytes": downloaded,
                            "total_bytes": total_bytes or None,
                            "speed": speed,
                            "eta": eta,
                            "percent": round(percent, 2),
                        })

        if progress_hook:
            progress_hook({
                "status": "finished",
                "downloaded_bytes": downloaded,
                "total_bytes": downloaded,
                "percent": 100.0,
            })

        return {
            "title": Path(filename).stem,
            "filename": str(target_path),
            "output_path": str(target_path),
            "filesize": downloaded,
            "ext": target_path.suffix.lstrip("."),
            "extractor": "direct_http",
        }
