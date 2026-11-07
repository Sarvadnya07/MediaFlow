import enum
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DownloadState(str, enum.Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Explicit valid state transition graph
VALID_TRANSITIONS: Dict[DownloadState, List[DownloadState]] = {
    DownloadState.QUEUED: [DownloadState.ANALYZING, DownloadState.DOWNLOADING, DownloadState.CANCELLED, DownloadState.FAILED],
    DownloadState.ANALYZING: [DownloadState.DOWNLOADING, DownloadState.FAILED, DownloadState.CANCELLED],
    DownloadState.DOWNLOADING: [DownloadState.PROCESSING, DownloadState.PAUSED, DownloadState.FAILED, DownloadState.CANCELLED],
    DownloadState.PAUSED: [DownloadState.DOWNLOADING, DownloadState.CANCELLED, DownloadState.FAILED],
    DownloadState.PROCESSING: [DownloadState.VERIFYING, DownloadState.FAILED, DownloadState.CANCELLED],
    DownloadState.VERIFYING: [DownloadState.COMPLETED, DownloadState.FAILED],
    DownloadState.COMPLETED: [],  # Terminal
    DownloadState.FAILED: [DownloadState.QUEUED],  # Allows Retry
    DownloadState.CANCELLED: [DownloadState.QUEUED],  # Allows Retry
}


class InvalidStateTransitionError(Exception):
    pass


class QueueItem(BaseModel):
    id: str
    url: str
    title: str = "Pending Analysis"
    state: DownloadState = DownloadState.QUEUED
    format_id: Optional[str] = None
    quality: Optional[str] = None
    subtitle_lang: Optional[str] = None
    output_dir: Optional[str] = None
    percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: float = 0.0
    eta: int = 0
    filepath: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    playlist_id: Optional[str] = None
    playlist_index: Optional[int] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def transition_to(self, new_state: DownloadState):
        """Validate state machine transition."""
        allowed = VALID_TRANSITIONS.get(self.state, [])
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid transition from '{self.state.value}' to '{new_state.value}' for job {self.id}."
            )
        self.state = new_state
        self.updated_at = time.time()
