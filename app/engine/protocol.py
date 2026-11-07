from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# Base Request / Response envelope with request-correlation IDs
class IPCRequest(BaseModel):
    id: str = Field(..., description="Unique correlation ID for the request")
    action: Literal[
        "initialize",
        "health_check",
        "analyze",
        "get_formats",
        "download",
        "cancel",
        "verify",
        "convert",
        "get_capabilities",
        "shutdown",
    ]
    payload: Dict[str, Any] = Field(default_factory=dict)


class IPCResponse(BaseModel):
    id: str = Field(..., description="Correlation ID matching the originating request")
    type: Literal["response", "event"] = "response"
    status: Literal["success", "error", "cancelled"] = "success"
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class ProgressEvent(BaseModel):
    id: str = Field(..., description="Job correlation ID")
    type: Literal["event"] = "event"
    event: Literal["progress", "state_change", "log"] = "progress"
    data: Dict[str, Any]


# Data models for analysis and formats
class MediaFormatInfo(BaseModel):
    format_id: str
    ext: str
    resolution: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    tbr: Optional[float] = None
    format_note: Optional[str] = None
    has_video: bool = False
    has_audio: bool = False


class MediaAnalysisResult(BaseModel):
    url: str
    extractor: str
    id: str
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None
    uploader: Optional[str] = None
    thumbnail: Optional[str] = None
    formats: List[MediaFormatInfo] = Field(default_factory=list)
    subtitles: List[str] = Field(default_factory=list)
    automatic_captions: List[str] = Field(default_factory=list)
    is_playlist: bool = False
    playlist_count: Optional[int] = None
