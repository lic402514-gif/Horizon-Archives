"""
File upload endpoints: generate upload URLs, record uploaded files.
In dev mode saves files locally; in prod uses OSS pre-signed URLs.
"""
import os
import re
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, File, User
from app.schemas import UploadRequest, UploadResponse, FileRecordRequest, FileOut
from app.auth import require_permission, STORAGE_DIR, generate_oss_key, get_upload_url, OSS_ENABLED

router = APIRouter(prefix="/api", tags=["upload"])

# Security: allowed file extensions and max upload size (100 MB)
ALLOWED_EXTENSIONS = {"pdf", "epub", "mobi", "azw3", "txt", "md", "doc", "docx", "djvu", "cbz", "cbr"}
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
_OSS_KEY_RE = re.compile(r"^[a-zA-Z0-9_\-./]+$")


def _validate_oss_key(oss_key: str) -> None:
    """Reject path traversal and illegal characters in oss_key."""
    if not oss_key or len(oss_key) > 512:
        raise HTTPException(400, "Invalid oss_key")
    if ".." in oss_key or oss_key.startswith("/") or oss_key.startswith("\\"):
        raise HTTPException(400, "Path traversal detected in oss_key")
    if not _OSS_KEY_RE.match(oss_key):
        raise HTTPException(400, "Illegal characters in oss_key")
    # Verify resolved path stays under STORAGE_DIR
    resolved = (Path(STORAGE_DIR) / oss_key).resolve()
    storage_root = Path(STORAGE_DIR).resolve()
    if not str(resolved).startswith(str(storage_root) + os.sep):
        raise HTTPException(400, "oss_key escapes storage directory")


@router.post("/upload-url", response_model=UploadResponse)
def generate_upload_url(
    body: UploadRequest,
    _u: User = Depends(require_permission("oss.upload")),
    db: Session = Depends(get_db),
):
    """Generate a pre-signed upload URL (in dev mode: returns local path info)."""
    book = db.query(Book).filter(Book.id == body.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    oss_key = generate_oss_key(body.book_id, body.format, body.filename)

    # OSS mode: return pre-signed PUT URL
    # Local mode: return direct upload endpoint
    if OSS_ENABLED:
        upload_url = get_upload_url(oss_key)
    else:
        upload_url = f"/api/upload-file?book_id={body.book_id}&format={body.format}&oss_key={oss_key}"

    return UploadResponse(upload_url=upload_url, oss_key=oss_key, expires_in=3600)


@router.post("/upload-file", response_model=FileOut)
async def upload_file_direct(
    book_id: int,
    format: str,
    oss_key: str,
    file: UploadFile = FastAPIFile(...),
    _u: User = Depends(require_permission("oss.upload")),
    db: Session = Depends(get_db),
):
    """Direct file upload for dev mode. Saves to local storage."""
    _validate_oss_key(oss_key)

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Validate extension
    ext = oss_key.rsplit(".", 1)[-1].lower() if "." in oss_key else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File extension .{ext} not allowed")

    # Save to local storage with size limit
    dest = Path(STORAGE_DIR) / oss_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"File too large (max {MAX_UPLOAD_SIZE // (1024*1024)} MB)")
    dest.write_bytes(content)

    # Record in DB
    file_record = File(
        book_id=book_id,
        format=format.upper(),
        oss_key=oss_key,
        size=len(content),
        sha256=None,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


@router.post("/files", response_model=FileOut, status_code=201)
def record_file(
    body: FileRecordRequest,
    _u: User = Depends(require_permission("oss.upload")),
    db: Session = Depends(get_db),
):
    """Record a file that was uploaded externally (e.g. via OSS pre-signed URL)."""
    book = db.query(Book).filter(Book.id == body.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    file_record = File(
        book_id=body.book_id,
        format=body.format.upper(),
        oss_key=body.oss_key,
        size=body.size,
        sha256=body.sha256,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record
