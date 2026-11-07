import shutil
import os
from abc import ABC, abstractmethod
from pathlib import Path
from ..logging_config import logger
from ..config import settings

class StorageProvider(ABC):
    @abstractmethod
    def upload_file(self, local_path: str, target_name: str) -> str:
        pass

class LocalStorageProvider(StorageProvider):
    def upload_file(self, local_path: str, target_name: str) -> str:
        # For local, 'upload' just means moving/keeping it in the downloads dir
        # Our yt_dlp already downloads to the target dir, so we just return the path
        logger.debug(f"Local storage: File already at {local_path}")
        return local_path

class S3StorageProvider(StorageProvider):
    def __init__(self):
        # In a real app, you'd initialize boto3 here
        # self.s3 = boto3.client('s3', ...)
        logger.info("S3 Storage Provider initialized (Stub)")

    def upload_file(self, local_path: str, target_name: str) -> str:
        # Mock S3 upload logic
        logger.info(f"MOCK: Uploading {local_path} to S3 bucket as {target_name}")
        # return f"https://{settings.S3_BUCKET}.s3.amazonaws.com/{target_name}"
        return f"s3://bucket/{target_name}"

def get_storage_provider() -> StorageProvider:
    # Logic to choose provider based on config
    # For now, we default to Local, but structure is ready for S3
    if getattr(settings, "USE_S3", False):
        return S3StorageProvider()
    return LocalStorageProvider()

storage_service = get_storage_provider()
