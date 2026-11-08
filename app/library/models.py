"""
MediaDock Local Media Library Models and Metadata Schema.
Supports categorized storage, tags, favorites, collections, and integrity checks.
"""
import enum
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MediaType(str, enum.Enum):
    VIDEO = "video"
    AUDIO = "audio"
    PLAYLIST = "playlist"
    UNKNOWN = "unknown"


class MediaItemRecord(Base):
    """Authoritative local media catalog table."""
    __tablename__ = "media_library"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    media_type = Column(String, default=MediaType.VIDEO.value)
    format = Column(String, nullable=True)  # mp4, mp3, mkv, etc.
    resolution = Column(String, nullable=True)  # 1920x1080, etc.
    duration = Column(Float, default=0.0)
    file_size = Column(Integer, default=0)
    thumbnail_path = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    uploader = Column(String, nullable=True)
    category = Column(String, default="General")
    tags = Column(String, default="")  # comma-separated tags
    is_favorite = Column(Boolean, default=False)
    collection_name = Column(String, nullable=True)
    is_missing = Column(Boolean, default=False)
    created_at = Column(Float, default=time.time)
    last_accessed = Column(Float, default=time.time)


class MediaItem(BaseModel):
    id: str
    title: str
    file_path: str
    media_type: MediaType = MediaType.VIDEO
    format: Optional[str] = None
    resolution: Optional[str] = None
    duration: float = 0.0
    file_size: int = 0
    thumbnail_path: Optional[str] = None
    source_url: Optional[str] = None
    uploader: Optional[str] = None
    category: str = "General"
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False
    collection_name: Optional[str] = None
    is_missing: bool = False
    created_at: float = Field(default_factory=time.time)
    last_accessed: float = Field(default_factory=time.time)


class LibraryStats(BaseModel):
    total_items: int = 0
    total_size_bytes: int = 0
    video_count: int = 0
    video_size_bytes: int = 0
    audio_count: int = 0
    audio_size_bytes: int = 0
    favorites_count: int = 0
    categories: Dict[str, int] = Field(default_factory=dict)
    disk_free_bytes: int = 0
    disk_total_bytes: int = 0
    managed_directories: List[str] = Field(default_factory=list)
