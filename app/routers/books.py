from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, case, asc, desc
from typing import Optional
import json, csv, io, codecs

from app.database import get_db
from app.models import Book, Author, Publisher, Category, Tag, User
from app.routers.activity import log_op
from app.schemas import (
    BookOut, BookCreate, BookUpdate,
    AuthorOut, AuthorCreate,
    PublisherOut, PublisherCreate,
    CategoryOut, CategoryCreate,
    TagOut, TagCreate,
)
from app.auth import require_permission, delete_oss_object

router = APIRouter(prefix="/api", tags=["books"])


# ── Search ───────────────────────────────────────────────────────────────────
@router.get("/search")
def search_books(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    term = f"%{q}%"
    base = db.query(Book).options(
        joinedload(Book.author),
        joinedload(Book.publisher),
        joinedload(Book.category),
        joinedload(Book.tags),
        joinedload(Book.files),
        joinedload(Book.book_assets_rel),
    ).outerjoin(Author, Book.author_id == Author.id)\
      .outerjoin(Publisher, Book.publisher_id == Publisher.id)\
      .filter(Book.status == "published")\
      .filter(or_(
          Book.title.ilike(term),
          Book.isbn.ilike(term),
          Book.summary.ilike(term),
          Author.name.ilike(term),
          Publisher.name.ilike(term),
          Book.category_code.ilike(term),
      ))

    total = base.distinct().count()
    results = base.distinct().order_by(Book.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for b in results:
        items.append({
            "id": b.id,
            "title": b.title,
            "author": b.author.name if b.author else None,
            "publisher": b.publisher.name if b.publisher else None,
            "isbn": b.isbn,
            "category_code": b.category_code,
            "category_name": b.category.name if b.category else None,
            "summary": (b.summary or "")[:200],
            "pub_year": b.pub_year,
            "has_download": (len(b.files) > 0 or len(b.book_assets_rel) > 0) if (b.files or b.book_assets_rel) else False,
            "tags": [t.name for t in (b.tags or [])],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── Books ───────────────────────────────────────────────────────────────────
@router.get("/books", response_model=list[BookOut])
def list_books(
    status: str | None = Query(None, description="Filter: draft, published"),
    category: str | None = Query(None, description="Category code"),
    db: Session = Depends(get_db),
):
    q = db.query(Book).options(
        joinedload(Book.author),
        joinedload(Book.publisher),
        joinedload(Book.category),
        joinedload(Book.tags),
        joinedload(Book.files),
    )
    if status:
        q = q.filter(Book.status == status)
    if category:
        q = q.filter(Book.category_code == category)
    return q.all()


# ── Data Grid query (MUST be before /books/{book_id} to avoid route conflict) 

SORTABLE_FIELDS = {
    "id": Book.id, "title": Book.title, "isbn": Book.isbn,
    "pub_year": Book.pub_year, "status": Book.status,
    "category_code": Book.category_code,
    "edition": Book.edition, "created_at": Book.created_at,
    "updated_at": Book.updated_at,
    "author": Author.name, "publisher": Publisher.name,
}


@router.get("/books/datagrid")
def books_datagrid(
    search: str = Query(None),
    filters: str = Query(None),
    sort: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Book).outerjoin(Author, Book.author_id == Author.id).outerjoin(Publisher, Book.publisher_id == Publisher.id)
    if search:
        term = f"%{search}%"
        q = q.filter(or_(Book.title.ilike(term), Book.isbn.ilike(term), Book.edition.ilike(term), Book.summary.ilike(term), Author.name.ilike(term), Publisher.name.ilike(term), Book.category_code.ilike(term)))
    if filters:
        try: fl = json.loads(filters)
        except: fl = []
        for f in fl:
            col = None; field = f.get("field",""); op = f.get("op","contains"); value = f.get("value","")
            if field == "author": col = Author.name
            elif field == "publisher": col = Publisher.name
            elif hasattr(Book, field): col = getattr(Book, field)
            if col is None: continue
            if op == "eq": q = q.filter(col == value)
            elif op == "neq": q = q.filter(col != value)
            elif op == "contains": q = q.filter(col.ilike(f"%{value}%"))
            elif op == "startswith": q = q.filter(col.ilike(f"{value}%"))
            elif op == "endswith": q = q.filter(col.ilike(f"%{value}"))
            elif op == "gt": q = q.filter(col > value)
            elif op == "lt": q = q.filter(col < value)
    if sort:
        for s in sort.split(","):
            parts = s.strip().split(":"); col = SORTABLE_FIELDS.get(parts[0].strip())
            if col: q = q.order_by(desc(col) if len(parts)>1 and parts[1].strip()=="desc" else asc(col))
    else: q = q.order_by(desc(Book.updated_at))
    total = q.count(); offset = (page-1)*page_size; rows = q.offset(offset).limit(page_size).all()
    return {"rows": [{"id":b.id,"title":b.title,"author":b.author.name if b.author else None,"author_id":b.author_id,"publisher":b.publisher.name if b.publisher else None,"publisher_id":b.publisher_id,"isbn":b.isbn,"edition":b.edition,"pub_year":b.pub_year,"category_code":b.category_code,"summary":(b.summary or "")[:200],"status":b.status,"created_at":b.created_at.isoformat() if b.created_at else None,"updated_at":b.updated_at.isoformat() if b.updated_at else None} for b in rows],"total":total,"page":page,"page_size":page_size,"total_pages":max(1,(total+page_size-1)//page_size)}


@router.get("/books/export/csv")
def export_books_csv(search: str=Query(None),sort: str=Query(None),_u: User=Depends(require_permission("book.export")),db: Session=Depends(get_db)):
    q = db.query(Book).outerjoin(Author,Book.author_id==Author.id).outerjoin(Publisher,Book.publisher_id==Publisher.id)
    if search:
        term=f"%{search}%"; q=q.filter(or_(Book.title.ilike(term),Book.isbn.ilike(term),Author.name.ilike(term),Publisher.name.ilike(term),Book.category_code.ilike(term)))
    if sort:
        for s in sort.split(","):
            parts=s.strip().split(":");col=SORTABLE_FIELDS.get(parts[0].strip())
            if col: q=q.order_by(desc(col) if len(parts)>1 and parts[1].strip()=="desc" else asc(col))
    else: q=q.order_by(Book.id)
    rows=q.all();out=io.StringIO();w=csv.writer(out)
    w.writerow(["id","title","author","publisher","isbn","edition","pub_year","category_code","summary","status"])
    for b in rows: w.writerow([b.id,b.title,b.author.name if b.author else "",b.publisher.name if b.publisher else "",b.isbn or "",b.edition or "",b.pub_year or "",b.category_code or "",(b.summary or "")[:500],b.status])
    out.seek(0)
    return StreamingResponse(iter([codecs.BOM_UTF8+out.getvalue().encode("utf-8")]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=books_export.csv"})


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = (
        db.query(Book)
        .options(
            joinedload(Book.author),
            joinedload(Book.publisher),
            joinedload(Book.category),
            joinedload(Book.tags),
            joinedload(Book.files),
        )
        .filter(Book.id == book_id)
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books", response_model=BookOut, status_code=201)
def create_book(
    body: BookCreate,
    request: Request,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    book = Book(
        title=body.title,
        author_id=body.author_id,
        publisher_id=body.publisher_id,
        isbn=body.isbn,
        edition=body.edition,
        pub_year=body.pub_year,
        category_code=body.category_code,
        summary=body.summary,
        status="draft",
    )
    if body.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(body.tag_ids)).all()
        book.tags = tags
    db.add(book)
    db.commit()
    db.refresh(book)
    log_op(db,_u,request,"create","book",str(book.id),book.title)
    # Re-fetch with relationships
    return (
        db.query(Book)
        .options(
            joinedload(Book.author),
            joinedload(Book.publisher),
            joinedload(Book.category),
            joinedload(Book.tags),
            joinedload(Book.files),
        )
        .filter(Book.id == book.id)
        .first()
    )


@router.put("/books/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    body: BookUpdate,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    book = (
        db.query(Book)
        .options(joinedload(Book.tags))
        .filter(Book.id == book_id)
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    update_data = body.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)

    for field, value in update_data.items():
        setattr(book, field, value)

    if tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
        book.tags = tags

    db.commit()
    db.refresh(book)
    return (
        db.query(Book)
        .options(
            joinedload(Book.author),
            joinedload(Book.publisher),
            joinedload(Book.category),
            joinedload(Book.tags),
            joinedload(Book.files),
        )
        .filter(Book.id == book.id)
        .first()
    )


@router.delete("/books/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    request: Request,
    _u: User = Depends(require_permission("book.delete")),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    # Delete associated OSS/local files first
    for f in book.files:
        delete_oss_object(f.oss_key)
    for ba in book.book_assets_rel:
        if ba.asset and ba.asset.oss_key:
            delete_oss_object(ba.asset.oss_key)
    db.delete(book)
    db.commit()
    log_op(db,_u,request,"delete","book",str(book_id),book.title)


# ── Authors ─────────────────────────────────────────────────────────────────
@router.get("/authors", response_model=list[AuthorOut])
def list_authors(db: Session = Depends(get_db)):
    return db.query(Author).all()


@router.post("/authors", response_model=AuthorOut, status_code=201)
def create_author(
    body: AuthorCreate,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    author = Author(name=body.name, bio=body.bio)
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


@router.put("/authors/{author_id}", response_model=AuthorOut)
def update_author(
    author_id: int,
    body: AuthorCreate,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    author.name = body.name
    author.bio = body.bio
    db.commit()
    db.refresh(author)
    return author


# ── Publishers ──────────────────────────────────────────────────────────────
@router.get("/publishers", response_model=list[PublisherOut])
def list_publishers(db: Session = Depends(get_db)):
    return db.query(Publisher).all()


@router.post("/publishers", response_model=PublisherOut, status_code=201)
def create_publisher(
    body: PublisherCreate,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    pub = Publisher(name=body.name, address=body.address)
    db.add(pub)
    db.commit()
    db.refresh(pub)
    return pub


# ── Categories ──────────────────────────────────────────────────────────────
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryCreate,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    cat = Category(code=body.code, name=body.name, parent_code=body.parent_code)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ── Tags ────────────────────────────────────────────────────────────────────
@router.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).all()


@router.post("/tags", response_model=TagOut, status_code=201)
def create_tag(
    body: TagCreate,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    existing = db.query(Tag).filter(Tag.name == body.name).first()
    if existing:
        return existing
    tag = Tag(name=body.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


# ── Batch import/update/delete via JSON upload ──────────────────────────────

def _resolve_author(db: Session, name: str) -> Author:
    """Find author by name, create if not exists."""
    author = db.query(Author).filter(Author.name == name).first()
    if not author:
        author = Author(name=name)
        db.add(author)
        db.flush()
    return author


def _resolve_publisher(db: Session, name: str) -> Publisher:
    """Find publisher by name, create if not exists."""
    pub = db.query(Publisher).filter(Publisher.name == name).first()
    if not pub:
        pub = Publisher(name=name)
        db.add(pub)
        db.flush()
    return pub


def _resolve_tags(db: Session, names: list[str]) -> list[Tag]:
    """Find tags by name, create missing ones."""
    tags = []
    for name in names:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


@router.post("/books/batch")
async def batch_books(
    file: UploadFile = File(...),
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    """
    Batch create/update/delete books via JSON upload.

    JSON format — array of objects, each with an `action` field:

    ```json
    [
      {
        "action": "create",
        "title": "书名",
        "author": "作者名",
        "publisher": "出版社名",
        "isbn": "978...",
        "edition": "第1版",
        "pub_year": 2020,
        "category_code": "I24",
        "summary": "简介",
        "tags": ["标签1", "标签2"],
        "status": "published"
      },
      {
        "action": "update",
        "id": 1,
        "title": "新书名",
        "category_code": "B2"
      },
      {
        "action": "delete",
        "id": 2
      }
    ]
    ```

    Notes:
    - `author` / `publisher` / `tags` resolved by name; auto-created if missing.
    - `update` supports partial fields — only provided fields are changed.
    - `delete` requires `id`.
    - Returns a summary of what was done.
    """
    raw = await file.read()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="JSON must be an array")

    results = {"created": 0, "updated": 0, "deleted": 0, "errors": []}

    for i, item in enumerate(items):
        action = item.get("action", "create")
        try:
            if action == "create":
                book = Book(
                    title=item["title"],
                    isbn=item.get("isbn"),
                    edition=item.get("edition"),
                    pub_year=item.get("pub_year"),
                    category_code=item.get("category_code"),
                    summary=item.get("summary"),
                    status=item.get("status", "draft"),
                )
                if item.get("author"):
                    book.author = _resolve_author(db, item["author"])
                if item.get("publisher"):
                    book.publisher = _resolve_publisher(db, item["publisher"])
                if item.get("tags"):
                    book.tags = _resolve_tags(db, item["tags"])
                db.add(book)
                db.flush()
                results["created"] += 1

            elif action == "update":
                book_id = item.get("id")
                if not book_id:
                    results["errors"].append(f"[{i}] update requires 'id'")
                    continue
                book = db.query(Book).filter(Book.id == book_id).first()
                if not book:
                    results["errors"].append(f"[{i}] book id={book_id} not found")
                    continue
                updatable = ["title","isbn","edition","pub_year","category_code","summary","status"]
                for k in updatable:
                    if k in item:
                        setattr(book, k, item[k])
                if "author" in item:
                    book.author = _resolve_author(db, item["author"])
                if "publisher" in item:
                    book.publisher = _resolve_publisher(db, item["publisher"])
                if "tags" in item:
                    book.tags = _resolve_tags(db, item["tags"])
                results["updated"] += 1

            elif action == "delete":
                book_id = item.get("id")
                if not book_id:
                    results["errors"].append(f"[{i}] delete requires 'id'")
                    continue
                book = db.query(Book).filter(Book.id == book_id).first()
                if not book:
                    results["errors"].append(f"[{i}] book id={book_id} not found")
                    continue
                db.delete(book)
                results["deleted"] += 1

            else:
                results["errors"].append(f"[{i}] unknown action '{action}'")

        except KeyError as e:
            results["errors"].append(f"[{i}] missing field: {e}")
        except Exception as e:
            results["errors"].append(f"[{i}] {e}")
            db.rollback()

    db.commit()
    return results


# ── Single create with author/publisher name resolution ─────────────────────
@router.post("/books/batch-create", status_code=201)
def single_create(
    body: dict,
    request: Request,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    """Create a single book with author/publisher resolved by name."""
    book = Book(
        title=body["title"],
        isbn=body.get("isbn"),
        edition=body.get("edition"),
        pub_year=body.get("pub_year"),
        category_code=body.get("category_code"),
        summary=body.get("summary"),
        status=body.get("status", "draft"),
    )
    if body.get("author"):
        book.author = _resolve_author(db, body["author"])
    if body.get("publisher"):
        book.publisher = _resolve_publisher(db, body["publisher"])
    db.add(book)
    db.commit()
    db.refresh(book)
    log_op(db,_u,request,"create","book",str(book.id),book.title)
    return {"id": book.id, "title": book.title}


# ── Batch edit with author/publisher name resolution ────────────────────────
@router.post("/books/batch-edit")
def batch_edit(
    payload: dict,
    _u: User = Depends(require_permission("book.create")),
    db: Session = Depends(get_db),
):
    """Batch-edit books. payload: {ids: [...], changes: {...}}"""
    ids = payload.get("ids", [])
    changes = payload.get("changes", {})
    updated = 0
    for book_id in ids:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            continue
        for key in ["title","isbn","edition","pub_year","category_code","summary","status"]:
            if key in changes:
                setattr(book, key, changes[key])
        if "author" in changes:
            book.author = _resolve_author(db, changes["author"])
        if "publisher" in changes:
            book.publisher = _resolve_publisher(db, changes["publisher"])
        updated += 1
    db.commit()
    return {"updated": updated}


# ── Batch delete ────────────────────────────────────────────────────────────
@router.post("/books/batch-delete")
def batch_delete(
    ids: list[int],
    _u: User = Depends(require_permission("book.delete")),
    db: Session = Depends(get_db),
):
    """Delete multiple books by ID."""
    deleted = 0
    for book_id in ids:
        book = db.query(Book).filter(Book.id == book_id).first()
        if book:
            db.delete(book)
            deleted += 1
    db.commit()
    return {"deleted": deleted}


@router.post("/books/{book_id}/assets", status_code=201)
def link_book_asset(book_id: int, body: dict,
                    _u: User = Depends(require_permission("book.create")),
                    db: Session = Depends(get_db)):
    from app.models import BookAsset
    ba = BookAsset(book_id=book_id, asset_id=body["asset_id"],
                   relation_type=body.get("role", "ebook"))
    db.add(ba); db.commit()
    return {"status": "linked", "id": ba.id}

