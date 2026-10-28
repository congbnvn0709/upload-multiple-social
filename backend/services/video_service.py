import shutil
from pathlib import Path
from typing import Dict, Any
from fastapi import UploadFile, HTTPException
from backend.config import UPLOAD_DIR

ALLOWED_EXTENSIONS = {".mp4", ".mov"}


def validate_video_file(filename: str | None) -> None:
    """
    Validate that the uploaded file has an allowed video extension (.mp4, .mov).
    Raises HTTPException(400) if invalid.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Only .mp4 and .mov are allowed."
        )


async def stage_uploaded_video(file: UploadFile) -> Dict[str, Any]:
    """
    Save uploaded video to the staging directory (temp_uploads/) and
    return its metadata including streaming URL for native HTML5 preview.
    """
    validate_video_file(file.filename)

    # Sanitize file name to avoid path traversal
    safe_filename = Path(file.filename or "").name
    destination = UPLOAD_DIR / safe_filename

    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Stream/write content to destination file
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = destination.stat().st_size
    stream_url = f"/media/{safe_filename}"

    return {
        "filename": safe_filename,
        "path": str(destination.resolve()),
        "size": size,
        "stream_url": stream_url,
    }
