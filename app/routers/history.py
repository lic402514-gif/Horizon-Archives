"""
Reading History API.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.auth import require_user
from app.models import User, ReadingHistory, Book, Author

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/user/reading-history")
def get_reading_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    action_type: str = Query(None),
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    q = (
        db.query(ReadingHistory)
        .options(joinedload(ReadingHistory.book).joinedload(Book.author))
        .filter(ReadingHistory.user_id == current_user.id)
    )
    if action_type:
        q = q.filter(ReadingHistory.action_type == action_type)
    q = q.order_by(ReadingHistory.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    rows = []
    for h in items:
        book = h.book
        rows.append({
            "id": h.id,
            "user_id": h.user_id,
            "book_id": h.book_id,
            "action_type": h.action_type,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "book": {
                "id": book.id,
                "title": book.title,
                "author": {"id": book.author.id, "name": book.author.name} if book.author else None,
                "isbn": book.isbn,
                "pub_year": book.pub_year,
                "category_code": book.category_code,
            } if book else None,
        })
    return {"rows": rows, "total": total, "page": page, "page_size": page_size}


@router.post("/user/reading-history", status_code=201)
def record_reading(
    body: dict,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    book_id = body.get("book_id")
    action_type = body.get("action_type", "view")
    if not book_id:
        return {"status": "error", "message": "缺少 book_id"}

    entry = ReadingHistory(
        user_id=current_user.id,
        book_id=book_id,
        action_type=action_type,
    )
    db.add(entry)
    db.commit()
    return {"status": "ok"}
