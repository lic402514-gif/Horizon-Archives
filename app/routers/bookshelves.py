"""
Bookshelves API — user book collections (want-to-read, reading, read).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.auth import require_user
from app.models import User, Bookshelf, BookshelfItem, Book

router = APIRouter(prefix="/api", tags=["bookshelves"])


def _bookshelf_out(shelf):
    return {
        "id": shelf.id,
        "user_id": shelf.user_id,
        "name": shelf.name,
        "is_public": shelf.is_public,
        "created_at": shelf.created_at.isoformat() if shelf.created_at else None,
        "book_count": len(shelf.items) if shelf.items else 0,
    }


def _book_out(book):
    return {
        "id": book.id,
        "title": book.title,
        "author": {"id": book.author.id, "name": book.author.name, "bio": book.author.bio} if book.author else None,
        "publisher": {"id": book.publisher.id, "name": book.publisher.name, "address": book.publisher.address} if book.publisher else None,
        "isbn": book.isbn,
        "edition": book.edition,
        "pub_year": book.pub_year,
        "category": {"code": book.category.code, "name": book.category.name} if book.category else None,
        "summary": book.summary,
        "cover_url": None,
        "status": book.status,
        "tags": [{"id": t.id, "name": t.name} for t in (book.tags or [])],
        "files": [],
        "created_at": book.created_at.isoformat() if book.created_at else None,
        "updated_at": book.updated_at.isoformat() if book.updated_at else None,
    }


@router.get("/bookshelves")
def list_bookshelves(current_user: User = Depends(require_user), db=Depends(get_db)):
    shelves = (
        db.query(Bookshelf)
        .options(joinedload(Bookshelf.items))
        .filter(Bookshelf.user_id == current_user.id)
        .order_by(Bookshelf.created_at.asc())
        .all()
    )
    if not shelves:
        # Auto-create default shelves
        defaults = ["想读", "在读", "已读"]
        for name in defaults:
            shelf = Bookshelf(user_id=current_user.id, name=name, is_public=True)
            db.add(shelf)
        db.commit()
        shelves = (
            db.query(Bookshelf)
            .options(joinedload(Bookshelf.items))
            .filter(Bookshelf.user_id == current_user.id)
            .order_by(Bookshelf.created_at.asc())
            .all()
        )
    return [_bookshelf_out(s) for s in shelves]


@router.get("/bookshelves/{shelf_id}")
def get_bookshelf(shelf_id: int, db=Depends(get_db)):
    shelf = (
        db.query(Bookshelf)
        .options(joinedload(Bookshelf.items).joinedload(BookshelfItem.book).joinedload(Book.author))
        .filter(Bookshelf.id == shelf_id)
        .first()
    )
    if not shelf:
        raise HTTPException(status_code=404, detail="书架不存在")
    # Check public access
    return {
        **_bookshelf_out(shelf),
        "items": [_book_out(item.book) for item in (shelf.items or []) if item.book],
    }


@router.post("/bookshelves", status_code=201)
def create_bookshelf(
    body: dict,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="书架名不能为空")
    is_public = body.get("is_public", True)
    shelf = Bookshelf(user_id=current_user.id, name=name, is_public=is_public)
    db.add(shelf)
    db.commit()
    db.refresh(shelf)
    return _bookshelf_out(shelf)


@router.put("/bookshelves/{shelf_id}")
def update_bookshelf(
    shelf_id: int,
    body: dict,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    shelf = db.query(Bookshelf).filter(Bookshelf.id == shelf_id, Bookshelf.user_id == current_user.id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="书架不存在")
    if "name" in body and body["name"]:
        shelf.name = body["name"].strip()
    if "is_public" in body:
        shelf.is_public = bool(body["is_public"])
    db.commit()
    db.refresh(shelf)
    return _bookshelf_out(shelf)


@router.delete("/bookshelves/{shelf_id}", status_code=204)
def delete_bookshelf(
    shelf_id: int,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    shelf = db.query(Bookshelf).filter(Bookshelf.id == shelf_id, Bookshelf.user_id == current_user.id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="书架不存在")
    db.delete(shelf)
    db.commit()


@router.post("/bookshelves/{shelf_id}/items", status_code=201)
def add_to_bookshelf(
    shelf_id: int,
    body: dict,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    shelf = db.query(Bookshelf).filter(Bookshelf.id == shelf_id, Bookshelf.user_id == current_user.id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="书架不存在")
    book_id = body.get("book_id")
    if not book_id:
        raise HTTPException(status_code=400, detail="缺少 book_id")
    existing = db.query(BookshelfItem).filter(
        BookshelfItem.bookshelf_id == shelf_id, BookshelfItem.book_id == book_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="已在此书架中")
    item = BookshelfItem(bookshelf_id=shelf_id, book_id=book_id)
    db.add(item)
    db.commit()
    return {"status": "ok"}


@router.delete("/bookshelves/{shelf_id}/items/{book_id}", status_code=204)
def remove_from_bookshelf(
    shelf_id: int,
    book_id: int,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    shelf = db.query(Bookshelf).filter(Bookshelf.id == shelf_id, Bookshelf.user_id == current_user.id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="书架不存在")
    item = db.query(BookshelfItem).filter(
        BookshelfItem.bookshelf_id == shelf_id, BookshelfItem.book_id == book_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="书籍不在书架中")
    db.delete(item)
    db.commit()


@router.get("/users/{user_id}/bookshelves")
def get_user_bookshelves(user_id: int, db=Depends(get_db)):
    shelves = (
        db.query(Bookshelf)
        .options(joinedload(Bookshelf.items))
        .filter(Bookshelf.user_id == user_id, Bookshelf.is_public == True)
        .order_by(Bookshelf.created_at.asc())
        .all()
    )
    return [_bookshelf_out(s) for s in shelves]
