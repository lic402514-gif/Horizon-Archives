"""Download endpoint: cookie-based auth, 302 redirect to file."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Book, File, User, DownloadLog, BookAsset, Asset
from app.auth import require_user, get_download_url

router = APIRouter(prefix="/api", tags=["download"])

@router.get("/download/{book_id}")
def download_book(book_id: int, format: str | None = Query(None),
                  current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book: raise HTTPException(404, "Book not found")
    oss_key, file_id = None, None
    f = db.query(File).filter(File.book_id == book_id)
    if format: f = f.filter(File.format == format.upper())
    fr = f.first()
    if fr: oss_key, file_id = fr.oss_key, fr.id
    if not oss_key:
        for ba in db.query(BookAsset).filter(BookAsset.book_id==book_id,
                BookAsset.relation_type.in_(['ebook','pdf','mobi','epub'])).all():
            if ba.asset and ba.asset.status=='active':
                if not format or (ba.asset.extension or '').lower()==format.lower():
                    oss_key=ba.asset.object_key; break
    if not oss_key: raise HTTPException(404, "File not found")
    if file_id: db.add(DownloadLog(user_id=current_user.id, file_id=file_id)); db.commit()
    return RedirectResponse(url=get_download_url(oss_key), status_code=302)
