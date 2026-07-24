"""
File upload endpoints: generate upload URLs, record uploaded files.
In dev mode saves files locally; in prod uses OSS pre-signed URLs.
"""
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, File, User
from app.schemas import UploadRequest, UploadResponse, FileRecordRequest, FileOut
from app.auth import require_permission, STORAGE_DIR, generate_oss_key, get_upload_url, OSS_ENABLED

router = APIRouter(prefix="/api", tags=["upload"])


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
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Save to local storage
    dest = (Path(STORAGE_DIR) / oss_key).resolve()
    if not str(dest).startswith(str(Path(STORAGE_DIR).resolve())):
        raise HTTPException(400, "Invalid file path")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Size limit: 100MB max
    content = await file.read()
    if len(content) > 104_857_600:
        raise HTTPException(400, "File too large (max 100MB)")
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
