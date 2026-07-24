"""
Integration API — allows the book-metadata-assistant to push books directly.
"""
import base64
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.auth import require_permission, STORAGE_DIR
from app.models import Book, Author, Publisher, Category, Asset, BookAsset, File as BookFile
from app.schemas import PushBookRequest, IsbnCheckResponse, BookOut

router = APIRouter(prefix="/api/integration", tags=["integration"])


@router.post("/check-isbn", response_model=IsbnCheckResponse)
def check_isbn(isbn: str = "", db=Depends(get_db)):
    if not isbn or not isbn.strip():
        return {"exists": False, "book": None}
    isbn = isbn.strip().replace("-", "").replace(" ", "")
    book = (
        db.query(Book)
        .options(
            joinedload(Book.author),
            joinedload(Book.publisher),
            joinedload(Book.category),
            joinedload(Book.tags),
            joinedload(Book.files),
        )
        .filter(Book.isbn == isbn)
        .first()
    )
    if book:
        # Build cover_url from BookAsset if available
        cover_url = None
        for ba in book.book_assets_rel:
            if ba.relation_type == "cover" and ba.asset:
                cover_url = ba.asset.url or f"/static-files/{ba.asset.object_key}"
                break
        book_out = BookOut(
            id=book.id,
            title=book.title,
            author=book.author,
            publisher=book.publisher,
            isbn=book.isbn,
            edition=book.edition,
            pub_year=book.pub_year,
            category=book.category,
            summary=book.summary,
            cover_url=cover_url,
            status=book.status,
            tags=[{"id": t.id, "name": t.name} for t in (book.tags or [])],
            files=[{"id": f.id, "book_id": f.book_id, "format": f.format,
                    "oss_key": f.oss_key, "size": f.size, "sha256": f.sha256,
                    "uploaded_at": f.uploaded_at} for f in (book.files or [])],
            created_at=book.created_at,
            updated_at=book.updated_at,
        )
        return {"exists": True, "book": book_out}
    return {"exists": False, "book": None}


@router.post("/push-book", status_code=201)
def push_book(
    body: PushBookRequest,
    _u=Depends(require_permission("book.create")),
    db=Depends(get_db),
):
    """Receive complete book metadata from the assistant and create records."""
    # Resolve or create author
    author_id = None
    if body.authors:
        author_name = body.authors[0].strip()
        author = db.query(Author).filter(Author.name == author_name).first()
        if not author:
            author = Author(name=author_name)
            db.add(author)
            db.flush()
        author_id = author.id

    # Resolve or create publisher
    publisher_id = None
    if body.publisher:
        pub = db.query(Publisher).filter(Publisher.name == body.publisher.strip()).first()
        if not pub:
            pub = Publisher(name=body.publisher.strip())
            db.add(pub)
            db.flush()
        publisher_id = pub.id

    # Resolve CLC category (accept partial match)
    category_code = None
    if body.clc:
        cat = db.query(Category).filter(Category.code == body.clc.strip()).first()
        if cat:
            category_code = cat.code

    # Parse pub_year
    pub_year = None
    if body.pub_year:
        try:
            pub_year = int(re.search(r"\d+", body.pub_year).group())
        except (ValueError, AttributeError):
            pass

    # Create book
    book = Book(
        title=body.title,
        author_id=author_id,
        publisher_id=publisher_id,
        isbn=body.isbn,
        edition=body.edition,
        pub_year=pub_year,
        category_code=category_code,
        summary=body.summary,
        status="published",
    )
    db.add(book)
    db.flush()

    created_assets = []

    # Save cover
    if body.cover_base64:
        cover_data = base64.b64decode(body.cover_base64)
        cover_dir = Path(STORAGE_DIR) / "covers"
        cover_dir.mkdir(parents=True, exist_ok=True)
        cover_filename = f"book_{book.id}_cover.png"
        cover_path = cover_dir / cover_filename
        cover_path.write_bytes(cover_data)

        asset = Asset(
            filename=cover_filename,
            extension="png",
            mime_type="image/png",
            size=len(cover_data),
            provider="local",
            object_key=f"covers/{cover_filename}",
            asset_type="cover",
            url=f"/static-files/covers/{cover_filename}",
        )
        db.add(asset)
        db.flush()

        ba = BookAsset(book_id=book.id, asset_id=asset.id, relation_type="cover")
        db.add(ba)
        created_assets.append(str(asset.id))

    # Save book file
    file_format = body.file_format or "pdf"
    if body.file_base64:
        file_data = base64.b64decode(body.file_base64)
        books_dir = Path(STORAGE_DIR) / "books"
        books_dir.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^\w]", "_", body.title)[:40]
        file_filename = f"{book.id}_{safe_title}.{file_format}"
        file_path = books_dir / file_filename
        file_path.write_bytes(file_data)

        bf = BookFile(
            book_id=book.id,
            format=file_format,
            oss_key=f"books/{file_filename}",
            size=len(file_data),
        )
        db.add(bf)

    db.commit()
    db.refresh(book)

    return {
        "id": book.id,
        "title": book.title,
        "status": book.status,
        "assets": created_assets,
    }
