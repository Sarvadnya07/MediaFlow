"""
Universal yt-dlp Provider Adapter.
Integrates the full spectrum of authorized yt-dlp extractors under the MediaDock provider interface.
"""
from typing import Any, Callable, Dict, Optional
import yt_dlp
from app.providers.base import BaseProvider, ProviderInfo, ProviderCapability
from app.engine.protocol import MediaAnalysisResult
from app.services import yt_service


class YtDlpProvider(BaseProvider):
    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="ytdlp_universal",
            name="yt-dlp Universal Media Adapter",
            description="Multi-source extractor engine supporting thousands of public web media platforms",
            version=getattr(yt_dlp, "__version__", "2026.03.01"),
            homepage="https://github.com/yt-dlp/yt-dlp",
            supported_domains=["youtube.com", "youtu.be", "vimeo.com", "soundcloud.com", "bandcamp.com", "twitch.tv", "*"],
            capabilities=ProviderCapability(
                video=True,
                audio=True,
                playlists=True,
                subtitles=True,
                metadata=True,
                chapters=True,
                thumbnails=True,
            ),
            status="active",
            requires_auth=False,
            notes="Authorized for public, unencrypted content. DRM circumvention is strictly prohibited."
        )

    def matches_url(self, url: str) -> bool:
        # Fallback universal matcher
        return bool(url and url.startswith(("http://", "https://")))

    def analyze(self, url: str, allow_private: bool = False) -> MediaAnalysisResult:
        return yt_service.analyze_url(url, allow_private=allow_private)

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
        return yt_service.download_stream(
            url=url,
            format_id=format_id,
            output_dir=output_dir,
            output_template=output_template,
            subtitle_lang=subtitle_lang,
            progress_callback=progress_hook,
            job_id=job_id,
            allow_private=allow_private,
        )
