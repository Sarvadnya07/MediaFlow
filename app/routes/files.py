from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

from ..config import settings

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/{filename}")
def get_file(filename: str):
    filepath = os.path.join(str(settings.DOWNLOADS_DIR), filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, filename=filename)
