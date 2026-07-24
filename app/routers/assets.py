"""
Asset Management — unified OSS resource lifecycle.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, asc, desc
from datetime import datetime, timezone
import os, json

from app.database import get_db, SessionLocal as SL
from app.models import Asset, BookAsset, Book, User
from app.auth import require_permission, require_user, STORAGE_DIR, OSS_ENABLED, generate_oss_key, get_upload_url

router = APIRouter(prefix="/api", tags=["assets"])

ASSET_TYPES = ["book","cover","article_image","thumbnail","preview","ocr","attachment","other"]
RELATION_TYPES = ["cover","ebook","pdf","mobi","preview","thumbnail","attachment"]


# ── Upload ──────────────────────────────────────────────────────────────────
@router.post("/assets/upload")
async def asset_upload(
    file: UploadFile = File(...),
    files: list[UploadFile] = File(default=None),
    asset_type: str = "other",
    remark: str = "",
    source: str = "",
    _u: User = Depends(require_permission("asset.create")),
    db: Session = Depends(get_db),
):
    """Upload a file, save to OSS/local, create Asset record."""
    if files and not file:
        file = files[0] if files else None
    content = await file.read()
    fn = file.filename or "untitled"
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    oss_key = generate_oss_key(0, ext, fn)  # book_id=0 for standalone assets

    if OSS_ENABLED:
        import oss2
        bucket = oss2.Bucket(oss2.Auth(os.getenv("OSS_ACCESS_KEY_ID",""), os.getenv("OSS_ACCESS_KEY_SECRET","")),
                             os.getenv("OSS_ENDPOINT",""), os.getenv("OSS_BUCKET_NAME",""))
        bucket.put_object(oss_key, content)
    else:
        from pathlib import Path
        dest = Path(STORAGE_DIR) / oss_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

    asset = Asset(
        filename=fn, extension=ext, mime_type=file.content_type,
        size=len(content), object_key=oss_key, asset_type=asset_type,
        remark=remark, upload_by=_u.id, status="active",
    )
    db.add(asset); db.commit(); db.refresh(asset)
    return _asset_dict(asset)


# ── DataGrid query ──────────────────────────────────────────────────────────
ASSET_SORT = {"id":Asset.id,"filename":Asset.filename,"extension":Asset.extension,
              "size":Asset.size,"asset_type":Asset.asset_type,"status":Asset.status,
              "upload_time":Asset.upload_time}

@router.get("/assets/datagrid")
def assets_datagrid(
    search: str = Query(None), filters: str = Query(None), sort: str = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=10, le=200),
    _u: User = Depends(require_user), db: Session = Depends(get_db),
):
    q = db.query(Asset)
    if search:
        t = f"%{search}%"; q = q.filter(or_(Asset.filename.ilike(t), Asset.object_key.ilike(t), Asset.remark.ilike(t)))
    if filters:
        try:
            for f in json.loads(filters):
                col = getattr(Asset, f["field"], None)
                if col is None: continue
                op, v = f.get("op","contains"), f.get("value","")
                if op == "eq": q = q.filter(col == v)
                elif op == "contains": q = q.filter(col.ilike(f"%{v}%"))
        except: pass
    if sort:
        for s in sort.split(","):
            p = s.strip().split(":"); col = ASSET_SORT.get(p[0])
            if col: q = q.order_by(desc(col) if len(p)>1 and p[1]=="desc" else asc(col))
    else: q = q.order_by(desc(Asset.upload_time))
    total = q.count(); rows = q.offset((page-1)*page_size).limit(page_size).all()
    return {"rows": [_asset_dict(r) for r in rows], "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total+page_size-1)//page_size)}


# ── CRUD ────────────────────────────────────────────────────────────────────
@router.get("/assets/{asset_id}")
def get_asset(asset_id: int, _u: User = Depends(require_user), db: Session = Depends(get_db)):
    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a: raise HTTPException(404, "Asset not found")
    return _asset_dict(a, detail=True)


@router.put("/assets/{asset_id}")
def update_asset(asset_id: int, body: dict, _u: User = Depends(require_permission("asset.create")), db: Session = Depends(get_db)):
    a = db.query(Asset).filter(Asset.id == asset_id).first()
    if not a: raise HTTPException(404, "Asset not found")
    for k in ["filename","remark","asset_type","status"]:
        if k in body: setattr(a, k, body[k])
    a.update_time = datetime.now(timezone.utc)
    db.commit()
    return _asset_dict(a)


@router.post("/assets/batch-delete")
def batch_delete_assets(body: dict, _u: User = Depends(require_permission("asset.delete")), db: Session = Depends(get_db)):
    """Logical delete: set status='deleted'."""
    ids = body.get("ids", [])
    db.query(Asset).filter(Asset.id.in_(ids)).update({"status": "deleted", "update_time": datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    return {"deleted": len(ids)}


@router.get("/assets/{asset_id}/refs")
def asset_refs(asset_id: int, _u: User = Depends(require_user), db: Session = Depends(get_db)):
    """Return books that reference this asset."""
    refs = db.query(BookAsset).filter(BookAsset.asset_id == asset_id).all()
    books = []
    for r in refs:
        b = db.query(Book).filter(Book.id == r.book_id).first()
        if b: books.append({"book_id": b.id, "title": b.title, "relation_type": r.relation_type})
    return {"asset_id": asset_id, "books": books}


# ── Book-Asset mapping ──────────────────────────────────────────────────────
@router.post("/book-assets")
def link_book_asset(body: dict, _u: User = Depends(require_permission("asset.create")), db: Session = Depends(get_db)):
    """Link an asset to a book: {book_id, asset_id, relation_type}."""
    ba = BookAsset(book_id=body["book_id"], asset_id=body["asset_id"], relation_type=body.get("relation_type","ebook"))
    db.add(ba); db.commit(); db.refresh(ba)
    return {"id": ba.id, "book_id": ba.book_id, "asset_id": ba.asset_id, "relation_type": ba.relation_type}


@router.get("/books/{book_id}/assets")
def book_assets(book_id: int, db: Session = Depends(get_db)):
    """Return all assets linked to a book."""
    bas = db.query(BookAsset).filter(BookAsset.book_id == book_id).all()
    return [{"id": ba.id, "asset_id": ba.asset_id, "relation_type": ba.relation_type,
             "filename": ba.asset.filename, "url": _asset_url(ba.asset)} for ba in bas]


@router.delete("/book-assets/{ba_id}", status_code=204)
def unlink_book_asset(ba_id: int, _u: User = Depends(require_permission("asset.create")), db: Session = Depends(get_db)):
    ba = db.query(BookAsset).filter(BookAsset.id == ba_id).first()
    if not ba: raise HTTPException(404, "Not found")
    db.delete(ba); db.commit()


# ── Helpers ─────────────────────────────────────────────────────────────────
def _asset_dict(a: Asset, detail: bool = False) -> dict:
    d = {"id": a.id, "filename": a.filename, "extension": a.extension, "mime_type": a.mime_type,
         "size": a.size, "asset_type": a.asset_type, "remark": a.remark,
         "upload_time": a.upload_time.isoformat() if a.upload_time else None,
         "status": a.status, "url": _asset_url(a),
         "uploader": None}
    if detail:
        d.update({"md5": a.md5, "sha256": a.sha256, "provider": a.provider,
                  "bucket": a.bucket, "object_key": a.object_key})
    return d


def _asset_url(a: Asset) -> str:
    k = a.object_key or ""
    if OSS_ENABLED:
        return get_upload_url(k)  # reuse pre-signed URL generator
    return f"/static-files/{k}"
