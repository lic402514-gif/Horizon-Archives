"""
Notification management API.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.auth import require_user, require_permission
from app.models import User, Notification

router = APIRouter(prefix="/api", tags=["notifications"])


def _notif_out(n):
    return {
        "id": n.id,
        "user_id": n.user_id,
        "title": n.title,
        "content": n.content,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/notifications")
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    q = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .count()
    )
    return {
        "rows": [_notif_out(n) for n in items],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
    }


@router.post("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    n.is_read = True
    db.commit()
    return {"status": "ok"}


@router.post("/notifications/read-all")
def mark_all_read(
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"status": "ok"}


@router.post("/notifications/send", status_code=201)
def send_notification(
    body: dict,
    _u: User = Depends(require_permission("notification.write")),
    db=Depends(get_db),
):
    """Send a notification to specific user(s). body: {user_ids: [...], title: str, content: str}"""
    user_ids = body.get("user_ids", [])
    title = body.get("title", "")
    content = body.get("content", "")
    if not user_ids or not title:
        raise HTTPException(status_code=400, detail="需要 user_ids 和 title")

    created = 0
    for uid in user_ids:
        n = Notification(user_id=uid, title=title, content=content)
        db.add(n)
        created += 1
    db.commit()
    return {"created": created}
