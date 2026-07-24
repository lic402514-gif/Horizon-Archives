"""
Online book preview — renders first N pages of a PDF as images.
"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.auth import STORAGE_DIR
from app.models import Book, File as BookFile

router = APIRouter(prefix="/api", tags=["preview"])


@router.get("/books/{book_id}/preview")
def get_book_preview(book_id: int, pages: int = 5, db=Depends(get_db)):
    """
    Return up to `pages` preview image URLs for a book.
    Images are extracted from the first PDF file associated with the book.
    """
    book = db.query(Book).options(joinedload(Book.files)).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    pdf_file = None
    for f in book.files:
        if f.format.lower() == "pdf":
            pdf_file = f
            break

    if not pdf_file:
        return {"pages": [], "message": "没有可预览的 PDF 文件"}

    # Get file path
    file_path = Path(STORAGE_DIR) / pdf_file.oss_key
    if not file_path.exists():
        return {"pages": [], "message": "文件不存在"}

    # Extract pages as base64 PNG images
    try:
        import fitz
        doc = fitz.open(str(file_path))
        max_pages = min(pages, len(doc), 10)
        page_images = []
        for i in range(max_pages):
            pix = doc[i].get_pixmap(dpi=120)
            import base64
            img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            page_images.append(f"data:image/png;base64,{img_b64}")
        doc.close()
        return {"pages": page_images, "total": len(doc), "shown": max_pages}
    except ImportError:
        return {"pages": [], "message": "服务器未安装 PyMuPDF，无法生成预览"}
    except Exception as e:
        return {"pages": [], "message": f"预览生成失败: {e}"}
