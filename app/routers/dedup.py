"""
Book deduplication and merge API.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import joinedload
from sqlalchemy import func as sa_func

from app.database import get_db
from app.auth import require_permission
from app.models import Book, User, BookComment, BookshelfItem, ReadingHistory, BookView, BookMergeLog, File as BookFile, BookAsset, DownloadLog

router = APIRouter(prefix="/api/books/dedup", tags=["dedup"])


@router.post("/scan")
def scan_duplicates(
    _u: User = Depends(require_permission("book.dedup")),
    db=Depends(get_db),
):
    """Find potential duplicate books by ISBN or similar titles."""
    duplicates = []

    # Find by duplicate ISBN
    isbn_dupes = (
        db.query(Book.isbn, sa_func.count(Book.id).label("cnt"))
        .filter(Book.isbn.isnot(None), Book.isbn != "")
        .group_by(Book.isbn)
        .having(sa_func.count(Book.id) > 1)
        .all()
    )
    for isbn, cnt in isbn_dupes:
        books = db.query(Book).filter(Book.isbn == isbn).all()
        duplicates.append({
            "type": "isbn",
            "key": isbn,
            "books": [{"id": b.id, "title": b.title, "status": b.status} for b in books],
        })

    # Find by same title (different publishers/ISBNs)
    title_dupes = (
        db.query(Book.title, sa_func.count(Book.id).label("cnt"))
        .filter(Book.title.isnot(None), Book.title != "")
        .group_by(Book.title)
        .having(sa_func.count(Book.id) > 1)
        .all()
    )
    for title, cnt in title_dupes:
        books = db.query(Book).filter(Book.title == title).all()
        # Only include if they have different ISBNs (real duplicates, not multi-volume)
        unique_isbns = set(b.isbn for b in books if b.isbn)
        if len(unique_isbns) <= 1:
            duplicates.append({
                "type": "title",
                "key": title,
                "books": [{"id": b.id, "title": b.title, "isbn": b.isbn, "status": b.status} for b in books],
            })

    return {"duplicates": duplicates, "total_groups": len(duplicates)}


@router.post("/merge")
def merge_books(
    body: dict,
    _u: User = Depends(require_permission("book.dedup")),
    db=Depends(get_db),
):
    """
    Merge source_book into target_book.
    Transfers: comments, bookshelf items, reading history, book views, files, assets.
    Deletes source_book afterward.
    """
    source_id = body.get("source_book_id")
    target_id = body.get("target_book_id")

    if not source_id or not target_id:
        raise HTTPException(status_code=400, detail="需要提供 source_book_id 和 target_book_id")

    source = db.query(Book).filter(Book.id == source_id).first()
    target = db.query(Book).filter(Book.id == target_id).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="图书不存在")

    # Transfer comments
    db.query(BookComment).filter(BookComment.book_id == source_id).update(
        {BookComment.book_id: target_id}, synchronize_session=False
    )

    # Transfer bookshelf items (remove duplicates)
    source_items = db.query(BookshelfItem).filter(BookshelfItem.book_id == source_id).all()
    for item in source_items:
        existing = db.query(BookshelfItem).filter(
            BookshelfItem.bookshelf_id == item.bookshelf_id,
            BookshelfItem.book_id == target_id,
        ).first()
        if existing:
            db.delete(item)
        else:
            item.book_id = target_id

    # Transfer reading history
    db.query(ReadingHistory).filter(ReadingHistory.book_id == source_id).update(
        {ReadingHistory.book_id: target_id}, synchronize_session=False
    )

    # Transfer book views
    db.query(BookView).filter(BookView.book_id == source_id).update(
        {BookView.book_id: target_id}, synchronize_session=False
    )

    # Transfer files
    db.query(BookFile).filter(BookFile.book_id == source_id).update(
        {BookFile.book_id: target_id}, synchronize_session=False
    )

    # Transfer book assets
    db.query(BookAsset).filter(BookAsset.book_id == source_id).update(
        {BookAsset.book_id: target_id}, synchronize_session=False
    )

    # Log the merge
    log_entry = BookMergeLog(
        source_book_id=source_id,
        target_book_id=target_id,
        merged_by=_u.id,
        merged_at=datetime.now(timezone.utc),
    )
    db.add(log_entry)

    # Delete source
    db.delete(source)
    db.commit()

    return {
        "status": "ok",
        "message": f"已将《{source.title}》(ID:{source_id}) 合并到《{target.title}》(ID:{target_id})",
    }
