from pydantic import BaseModel
from typing import Optional

class DownloadRequest(BaseModel):
    url: str
    quality: Optional[str] = None
    webhook_url: Optional[str] = None

class DownloadResponse(BaseModel):
    id: int
    url: str
    title: str
    filepath: str
    thumbnail_path: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    status: str
    progress: int
    error_message: Optional[str] = None
    created_at: str

class ConvertRequest(BaseModel):
    file: str
    format: str

class MetadataRequest(BaseModel):
    file: str
    title: Optional[str] = None
    artist: Optional[str] = None
    thumbnail: Optional[str] = None

class StartDownloadResponse(BaseModel):
    job_id: int

class ConversionResponse(BaseModel):
    status: str
    output_file: str

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
