"""In-app messaging system."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import require_user
from app.models import User, Message

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _msg_out(m):
    return {
        "id": m.id, "sender_id": m.sender_id, "receiver_id": m.receiver_id,
        "subject": m.subject, "content": m.content, "is_read": m.is_read,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "sender_name": m.sender.username if m.sender else "?",
        "receiver_name": m.receiver.username if m.receiver else "?",
    }


@router.get("/inbox")
def inbox(page: int = Query(1, ge=1), page_size: int = Query(20, ge=5, le=100),
          u: User = Depends(require_user), db: Session = Depends(get_db)):
    q = db.query(Message).options(joinedload(Message.sender)).filter(
        Message.receiver_id == u.id
    ).order_by(Message.created_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"rows": [_msg_out(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/outbox")
def outbox(page: int = Query(1, ge=1), page_size: int = Query(20, ge=5, le=100),
           u: User = Depends(require_user), db: Session = Depends(get_db)):
    q = db.query(Message).options(joinedload(Message.receiver)).filter(
        Message.sender_id == u.id
    ).order_by(Message.created_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"rows": [_msg_out(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/unread-count")
def unread_count(u: User = Depends(require_user), db: Session = Depends(get_db)):
    count = db.query(Message).filter(
        Message.receiver_id == u.id, Message.is_read == False
    ).count()
    return {"count": count}


@router.post("", status_code=201)
def send(body: dict, u: User = Depends(require_user), db: Session = Depends(get_db)):
    subject = (body.get("subject") or "").strip()
    content = (body.get("content") or "").strip()
    if not subject or not content:
        raise HTTPException(400, "subject and content are required")
    # Support both receiver_id and receiver_name
    receiver_id = body.get("receiver_id")
    receiver_name = (body.get("receiver_name") or "").strip()
    if receiver_name:
        receiver = db.query(User).filter(User.username == receiver_name).first()
        if receiver: receiver_id = receiver.id
    if not receiver_id:
        raise HTTPException(400, "receiver not found")
    msg = Message(sender_id=u.id, receiver_id=receiver_id, subject=subject, content=content)
    db.add(msg); db.commit(); db.refresh(msg)
    return _msg_out(msg)


@router.put("/{msg_id}/read")
def mark_read(msg_id: int, u: User = Depends(require_user), db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == msg_id, Message.receiver_id == u.id).first()
    if not msg: raise HTTPException(404)
    msg.is_read = True; db.commit()
    return {"status": "ok"}


@router.delete("/{msg_id}")
def delete_msg(msg_id: int, u: User = Depends(require_user), db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == msg_id).filter(
        (Message.sender_id == u.id) | (Message.receiver_id == u.id)
    ).first()
    if not msg: raise HTTPException(404)
    db.delete(msg); db.commit()
    return {"status": "ok"}
