"""
Operation log writer + public activity feed.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import OperationLog, User

router = APIRouter(prefix="/api", tags=["activity"])

# Actions that are NOT public (login, download, etc.)
_PRIVATE_ACTIONS = {"login", "logout", "download", "reset_password"}


def log_op(db: Session, user: User, request: Request | None,
           action: str, target_type: str, target_id: str = "",
           detail: str = "", result: str = "success"):
    """Write one operation log entry."""
    is_public = action not in _PRIVATE_ACTIONS
    ip = request.client.host if request and request.client else ""
    entry = OperationLog(
        user_id=user.id, action=action, target_type=target_type,
        target_id=str(target_id), detail=detail, ip_address=ip,
        result=result, is_public=is_public,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(entry)


# ── Public Activity Feed ────────────────────────────────────────────────────

PUBLIC_DESC = {
    ("create","book"):    lambda d: f"创建了图书《{d}》",
    ("update","book"):    lambda d: f"修改了图书《{d}》",
    ("delete","book"):    lambda d: f"删除了图书《{d}》",
    ("publish","book"):   lambda d: f"发布了图书《{d}》",
    ("create","article"): lambda d: f"发布了文章《{d}》",
    ("update","article"): lambda d: f"修改了文章《{d}》",
    ("delete","article"): lambda d: f"删除了文章《{d}》",
    ("publish","article"):lambda d: f"发布了文章《{d}》",
    ("upload","asset"):   lambda d: f"上传了 1 个数字资源",
    ("delete","asset"):   lambda d: f"删除了 1 个数字资源",
    ("create","user"):    lambda d: f"创建了用户 {d}",
    ("ban","user"):       lambda d: f"封禁了用户 {d}",
    ("unban","user"):     lambda d: f"解封了用户 {d}",
    ("assign_role","user"):lambda d: f"修改了用户 {d} 的角色",
    ("create","invite_code"):lambda d: "创建了 1 个邀请码",
    ("create","author"):  lambda d: f"新增了作者 {d}",
    ("update","author"):  lambda d: f"修改了作者 {d}",
    ("delete","author"):  lambda d: f"删除了作者 {d}",
    ("create","publisher"):lambda d: f"新增了出版社 {d}",
    ("update","publisher"):lambda d: f"修改了出版社 {d}",
    ("delete","publisher"):lambda d: f"删除了出版社 {d}",
    ("create","tag"):     lambda d: f"新增了标签 {d}",
    ("update","tag"):     lambda d: f"修改了标签 {d}",
    ("delete","tag"):     lambda d: f"删除了标签 {d}",
    ("create","role"):    lambda d: f"创建了角色 {d}",
    ("delete","role"):    lambda d: f"删除了角色 {d}",
    ("assign_permission","role"):lambda d: f"修改了角色 {d} 的权限",
    ("rebuild","system"): lambda d: "重建了整站静态页面",
}


@router.get("/activity/timeline")
def activity_timeline(db: Session = Depends(get_db)):
    """Return dates (last 7 days) with public log counts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    rows = (
        db.query(func.date(OperationLog.timestamp), func.count(OperationLog.id))
        .filter(OperationLog.timestamp >= cutoff, OperationLog.is_public == True)
        .group_by(func.date(OperationLog.timestamp))
        .order_by(func.date(OperationLog.timestamp).desc())
        .all()
    )
    return [{"date": str(r[0]), "count": r[1]} for r in rows]


@router.get("/activity")
def activity_day(date: str = Query(...), page: int = 1, page_size: int = 50,
                 db: Session = Depends(get_db)):
    """Return public logs for a specific date."""
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format, use YYYY-MM-DD")

    next_day = d + timedelta(days=1)
    total = db.query(OperationLog).filter(
        OperationLog.timestamp >= d, OperationLog.timestamp < next_day,
        OperationLog.is_public == True
    ).count()

    entries = db.query(OperationLog).filter(
        OperationLog.timestamp >= d, OperationLog.timestamp < next_day,
        OperationLog.is_public == True
    ).order_by(OperationLog.timestamp.asc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Resolve operator usernames
    user_ids = {e.user_id for e in entries if e.user_id}
    users = {}
    if user_ids:
        users = {u.id: u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    result = []
    for e in entries:
        key = (e.action, e.target_type)
        desc_fn = PUBLIC_DESC.get(key, lambda d: f"{e.action} {e.target_type}")
        description = desc_fn(e.detail or "")
        result.append({
            "id": e.id,
            "time": e.timestamp.strftime("%H:%M") if e.timestamp else "",
            "operator": users.get(e.user_id, "系统"),
            "action": e.action,
            "target_type": e.target_type,
            "target_name": e.detail or e.target_id,
            "description": description,
            "result": e.result,
        })

    return {"date": date, "total": total, "page": page, "entries": result}
