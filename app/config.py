from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "YT-DLP Backend API"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "SET_A_SECURE_SECRET_KEY_IN_ENV"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    DATABASE_URL: str = "sqlite:///./downloads.db"
    
    # Celery / Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Storage
    USE_S3: bool = False
    S3_BUCKET: str = "my-media-bucket"
    S3_REGION: str = "us-east-1"
    
    # Paths
    DOWNLOADS_DIR: Path = Path("downloads")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure downloads directory exists
settings.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
