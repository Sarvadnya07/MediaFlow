from fastapi import FastAPI, Request, status, APIRouter
from fastapi.responses import JSONResponse
import shutil
from .database import engine, Base
from . import models
from .routes import downloads, files, auth_routes, websockets
from .config import settings
from .logging_config import logger
from .rate_limiter import rate_limiter
from fastapi import Depends

logger.info("Starting YT-DLP Backend API startup sequence...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A FastAPI backend for downloading and converting video/audio using yt-dlp and ffmpeg.",
    dependencies=[Depends(rate_limiter)]
)

# API Versioning: v1
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_routes.router)
v1_router.include_router(downloads.router)
v1_router.include_router(files.router)
v1_router.include_router(websockets.router)

app.include_router(v1_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log detailed internal stack trace strictly to internal logs
    logger.error(f"Global exception caught on {request.url.path}: {str(exc)}", exc_info=True)
    
    # Return sanitized generic response to client to prevent internal system leaks
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
    )


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "version": "1.0.0"}


@app.get("/health", tags=["System"])
def health_check():
    """Check if critical system dependencies are installed."""
    import importlib.util
    ffmpeg_installed = shutil.which("ffmpeg") is not None
    yt_dlp_installed = importlib.util.find_spec("yt_dlp") is not None

    logger.debug(f"Health check: FFmpeg={ffmpeg_installed}, yt-dlp={yt_dlp_installed}")

    return {
        "status": "healthy" if ffmpeg_installed and yt_dlp_installed else "degraded",
        "dependencies": {
            "ffmpeg": "installed" if ffmpeg_installed else "missing",
            "yt-dlp": "installed" if yt_dlp_installed else "missing"
        }
    }
