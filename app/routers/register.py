"""Registration + invite code endpoints."""
import random, string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, InviteCode, Role
from app.auth import hash_password, create_access_token, require_permission, require_user

router = APIRouter(prefix="/api", tags=["register"])


def _gen_code():
    """Generate an 8-character alphanumeric invite code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ── Invite Code CRUD (admin) ────────────────────────────────────────────────

@router.get("/invite-codes")
def list_invite_codes(_u: User = Depends(require_permission("user.read")),
                      db: Session = Depends(get_db)):
    codes = db.query(InviteCode).order_by(InviteCode.created_at.desc()).limit(100).all()
    return [{"id": c.id, "code": c.code, "status": c.status, "note": c.note,
             "max_uses": c.max_uses, "use_count": c.use_count,
             "expires_at": c.expires_at.isoformat() if c.expires_at else None,
             "created_at": c.created_at.isoformat() if c.created_at else None,
             "used_by": c.used_by} for c in codes]


@router.post("/invite-codes", status_code=201)
def create_invite_code(body: dict, _u: User = Depends(require_permission("user.create")),
                       db: Session = Depends(get_db)):
    code_str = body.get("code") or _gen_code()
    while db.query(InviteCode).filter(InviteCode.code == code_str).first():
        code_str = _gen_code()

    days = body.get("expire_days", 30)
    expires = datetime.now(timezone.utc) + timedelta(days=int(days)) if days else None

    c = InviteCode(code=code_str, created_by=_u.id, note=body.get("note"),
                   max_uses=int(body.get("max_uses", 1)), expires_at=expires)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "code": c.code, "note": c.note, "max_uses": c.max_uses,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None}


@router.delete("/invite-codes/{code_id}", status_code=204)
def delete_invite_code(code_id: int, _u: User = Depends(require_permission("user.create")),
                       db: Session = Depends(get_db)):
    c = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not c: raise HTTPException(404, "Invite code not found")
    db.delete(c); db.commit()


@router.post("/invite-codes/{code_id}/expire", status_code=200)
def expire_invite_code(code_id: int, _u: User = Depends(require_permission("user.create")),
                       db: Session = Depends(get_db)):
    c = db.query(InviteCode).filter(InviteCode.id == code_id).first()
    if not c: raise HTTPException(404, "Invite code not found")
    c.status = "expired"; db.commit()
    return {"status": "expired"}


# ── Username availability check ──────────────────────────────────────────────
@router.get("/check-username")
def check_username(username: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Check if a username is already taken. No auth needed."""
    exists = db.query(User).filter(User.username == username.strip()).first()
    return {"username": username.strip(), "available": not exists, "message": "用户名可用" if not exists else "用户名已被注册"}


# ── Registration ────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(body: dict, db: Session = Depends(get_db)):
    # Validate invite code
    code_str = body.get("invite_code", "").strip().upper()
    if not code_str:
        raise HTTPException(400, "缺少邀请码")

    invite = db.query(InviteCode).filter(
        InviteCode.code == code_str,
        InviteCode.status == "unused"
    ).first()

    if not invite:
        raise HTTPException(400, "邀请码无效或已过期")
    if invite.expires_at and invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        invite.status = "expired"; db.commit()
        raise HTTPException(400, "邀请码已过期")
    if invite.use_count >= invite.max_uses:
        raise HTTPException(400, "邀请码已被使用")

    # Validate username / password
    username = (body.get("username") or "").strip()
    password = body.get("password", "")
    if not username or len(username) < 2:
        raise HTTPException(400, "用户名至少2个字符")
    if len(password) < 4:
        raise HTTPException(400, "密码至少4个字符")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "用户名已存在")

    # Create user
    user = User(
        username=username,
        password_hash=hash_password(password),
        qq=(body.get("qq") or "").strip() or None,
        phone=(body.get("phone") or "").strip() or None,
        wechat=(body.get("wechat") or "").strip() or None,
        invite_code_used=code_str,
        status="ACTIVE",
        role="user",
    )
    db.add(user); db.flush()

    # Mark invite code as used
    invite.used_by = user.id
    invite.use_count += 1
    if invite.use_count >= invite.max_uses:
        invite.status = "used"

    # Auto-assign Member role
    member = db.query(Role).filter(Role.name == "Member").first()
    if member:
        user.roles.append(member)

    db.commit(); db.refresh(user)

    # Generate token + set cookie for immediate login
    token = create_access_token({"sub": str(user.id), "role": user.role})
    resp = JSONResponse({"user_id": user.id, "username": user.username, "message": "注册成功"})
    resp.set_cookie(key="session", value=token, httponly=False, max_age=86400, samesite="lax", path="/")
    return resp
