"""Quotes CRUD API."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import require_permission, require_user
from sqlalchemy import text

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.get("")
def list_quotes(_u: User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id,content,author,asset_id,sort_order,status FROM quotes ORDER BY sort_order")).mappings().all()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_quote(body: dict, _u: User = Depends(require_permission("article.create")),
                 db: Session = Depends(get_db)):
    db.execute(text("INSERT INTO quotes(content,author,asset_id,sort_order,status) VALUES(:c,:a,:aid,:so,:s)"),
               {"c": body["content"], "a": body.get("author", ""), "aid": body.get("asset_id"),
                "so": body.get("sort_order", 0), "s": body.get("status", "active")})
    db.commit()
    return {"status": "created"}


@router.put("/{qid}")
def update_quote(qid: int, body: dict, _u: User = Depends(require_permission("article.create")),
                 db: Session = Depends(get_db)):
    sets = []; params = {"id": qid}
    for f in ["content", "author", "asset_id", "sort_order", "status"]:
        if f in body:
            sets.append(f"{f} = :{f}")
            params[f] = body[f]
    if sets:
        db.execute(text(f"UPDATE quotes SET {', '.join(sets)} WHERE id = :id"), params)
        db.commit()
    return {"status": "updated"}


@router.delete("/{qid}")
def delete_quote(qid: int, _u: User = Depends(require_permission("article.create")),
                 db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM quotes WHERE id = :id"), {"id": qid})
    db.commit()
    return {"deleted": True}
