"""
MediaDock Provider Ecosystem — Base Provider Interface and Capability Model.
Defines clean, extensible contracts for media source integration.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from app.engine.protocol import MediaAnalysisResult


class ProviderCapability(BaseModel):
    video: bool = True
    audio: bool = True
    playlists: bool = True
    subtitles: bool = True
    metadata: bool = True
    chapters: bool = True
    thumbnails: bool = True


class ProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    version: str
    homepage: str
    supported_domains: List[str]
    capabilities: ProviderCapability
    status: str = "active"  # "active", "degraded", "disabled"
    requires_auth: bool = False
    notes: Optional[str] = None


class BaseProvider(ABC):
    """
    Abstract base class that all MediaDock providers must implement.
    Separates URL recognition, metadata extraction, format discovery, and downloading.
    """

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return provider metadata and capability declarations."""
        pass

    @abstractmethod
    def matches_url(self, url: str) -> bool:
        """Return True if this provider can handle the given URL."""
        pass

    @abstractmethod
    def analyze(self, url: str, allow_private: bool = False) -> MediaAnalysisResult:
        """Extract media metadata and stream options without downloading."""
        pass

    @abstractmethod
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
        """Execute media download with progress reporting and cancellation support."""
        pass

    def check_health(self) -> Dict[str, Any]:
        """Provider diagnostic self-test."""
        return {
            "id": self.info.id,
            "status": "healthy",
            "version": self.info.version,
            "compatible": True,
        }
