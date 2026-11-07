from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from ..config import settings
from ..security import ensure_within_directory, SecurityError

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{filename}")
def get_file(filename: str):
    """
    Safely retrieve a file from the downloads directory.
    Secured against directory traversal attacks.
    """
    downloads_dir = Path(settings.DOWNLOADS_DIR).resolve()
    target_path = downloads_dir / filename

    try:
        # Strictly assert target is within DOWNLOADS_DIR
        safe_path = ensure_within_directory(target_path, downloads_dir)
    except SecurityError:
        raise HTTPException(status_code=403, detail="Access denied: invalid file path.")

    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(str(safe_path), filename=safe_path.name)
