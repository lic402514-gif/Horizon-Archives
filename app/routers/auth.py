from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Role, Permission, InviteCode, user_roles, role_permissions
from app.schemas import (
    LoginRequest, TokenResponse, UserOut, UserCreate, UserUpdate,
)
from app.auth import (
    verify_password, hash_password, create_access_token,
    require_user, require_permission, get_current_user, oplog,
)

router = APIRouter(prefix="/api", tags=["auth"])


# ── Login / Token ───────────────────────────────────────────────────────────
@router.post("/token", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Account is not active")
    # Increment token version — invalidates all existing sessions for this user
    user.token_version = (user.token_version or 1) + 1
    db.commit()
    token = create_access_token({"sub": str(user.id), "role": user.role}, user.token_version)
    # Log with IP
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    oplog(db, user, "login", "user", str(user.id), f"IP: {ip}", ip)
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"access_token": token, "token_type": "bearer"})
    resp.set_cookie(
        key="session", value=token,
        httponly=True,  # Prevent XSS token theft
        max_age=86400, samesite="lax", path="/"
    )
    return resp


# ── Current user + permissions ──────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(require_user)):
    return UserOut.from_orm_user(current_user)


@router.put("/users/me/avatar")
def update_avatar(body: dict, current_user: User = Depends(require_user),
                  db: Session = Depends(get_db)):
    asset_id = body.get("asset_id")
    current_user.avatar_asset_id = asset_id
    db.commit()
    db.refresh(current_user)
    return {"avatar_asset_id": asset_id}


@router.get("/me/permissions")
def my_permissions(current_user: User = Depends(require_user)):
    """Return current user's permissions and roles."""
    return {
        "permissions": sorted(current_user.get_permissions()),
        "roles": [{"id": r.id, "name": r.name} for r in current_user.roles],
    }


# ── User management ─────────────────────────────────────────────────────────
@router.get("/users")
def list_users(_u: User = Depends(require_permission("user.read")), db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    users = db.query(User).options(joinedload(User.roles).joinedload(Role.permissions)).order_by(User.id).all()
    return [UserOut.from_orm_user(u) for u in users]


# ── Easter egg ──
@router.get("/me/easter-egg")
def check_easter_egg(current_user: User = Depends(require_user)):
    # Super admin always has access; others need explicit grant
    is_admin = any(r.name == "Super Admin" for r in (current_user.roles or []))
    return {"has_easter_egg": bool(current_user.has_easter_egg or is_admin)}

@router.put("/users/{user_id}/easter-egg")
def grant_easter_egg(user_id: int, body: dict,
    _u: User = Depends(require_permission("system.config")),
    db: Session = Depends(get_db)):
    grant = body.get("grant", False)
    if grant:
        db.query(User).filter(User.has_easter_egg == True).update({"has_easter_egg": False})
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    user.has_easter_egg = grant
    db.commit()
    return {"status": "ok", "has_easter_egg": grant}


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    _u: User = Depends(require_permission("user.create")),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        email=body.email,
        role=body.role,
        status=body.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_user(user)


@router.put("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    body: UserUpdate,
    _u: User = Depends(require_permission("user.assign_role")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is not None:
        user.role = body.role
    if body.status is not None:
        user.status = body.status
    if body.email is not None:
        user.email = body.email
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_user(user)


@router.put("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    body: dict,
    _u: User = Depends(require_permission("user.reset_password")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(body["password"])
    db.commit()
    return {"status": "ok"}


@router.put("/users/{user_id}/ban", response_model=UserOut)
def ban_user(
    user_id: int,
    _u: User = Depends(require_permission("user.disable")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "BANNED"
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_user(user)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: dict,
                current_user: User = Depends(require_user),
                db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only admins can modify other users; users can only modify themselves
    is_admin = current_user.role == "admin"
    if not is_admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot modify other users")

    for field in ["username","email","qq","phone","wechat","public_fields"]:
        if field in body:
            setattr(user, field, body[field])

    # Only admins can change status or role
    if is_admin:
        if "status" in body and body["status"] in ("ACTIVE","DISABLED","BANNED"):
            user.status = body["status"]
        if "role" in body and body["role"] in ("admin","user"):
            user.role = body["role"]
    db.commit()
    db.refresh(user)
    from app.schemas import UserOut
    return UserOut(
        id=user.id, username=user.username, email=user.email or "",
        role=user.role or "", status=user.status or "ACTIVE",
        created_at=user.created_at or "",
        roles=[{"id": r.id, "name": r.name, "perm_count": len(r.permissions)} for r in (user.roles or [])],
        avatar_url=None, avatar_asset_id=user.avatar_asset_id,
        qq=user.qq, phone=user.phone, wechat=user.wechat,
        invite_code_used=user.invite_code_used, has_easter_egg=user.has_easter_egg
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    _u: User = Depends(require_permission("user.delete")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == _u.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    # 清除所有关联数据
    db.execute(user_roles.delete().where(user_roles.c.user_id == user_id))
    db.query(InviteCode).filter(InviteCode.used_by == user_id).update({"used_by": None, "status": "unused"})
    db.query(InviteCode).filter(InviteCode.created_by == user_id).update({"created_by": None})
    from app.models import OperationLog, BookComment, ArticleComment, Bookshelf, Message, Notification, DownloadLog, Asset
    db.query(OperationLog).filter(OperationLog.user_id == user_id).update({"user_id": None})
    db.query(BookComment).filter(BookComment.user_id == user_id).delete()
    db.query(ArticleComment).filter(ArticleComment.user_id == user_id).delete()
    db.query(Bookshelf).filter(Bookshelf.user_id == user_id).delete()
    db.query(Message).filter((Message.sender_id == user_id) | (Message.receiver_id == user_id)).delete()
    db.query(Notification).filter(Notification.user_id == user_id).delete()
    db.query(DownloadLog).filter(DownloadLog.user_id == user_id).update({"user_id": None})
    db.query(Asset).filter(Asset.upload_by == user_id).update({"upload_by": None})
    db.delete(user)
    db.commit()


# ── Role management ─────────────────────────────────────────────────────────
@router.get("/roles")
def list_roles(
    _u: User = Depends(require_permission("role.read")),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "description": r.display_name,
             "permissions": [p.code for p in r.permissions]} for r in roles]


@router.post("/roles", status_code=201)
def create_role(
    body: dict,
    _u: User = Depends(require_permission("role.create")),
    db: Session = Depends(get_db),
):
    name = body["name"]
    description = body.get("description", "")
    existing = db.query(Role).filter(Role.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")
    role = Role(name=name, display_name=description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"id": role.id, "name": role.name}


@router.put("/roles/{role_id}/permissions")
def assign_role_permissions(
    role_id: int,
    permission_codes: list[str],
    _u: User = Depends(require_permission("permission.assign")),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    # Clear existing permissions for this role
    db.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))
    # Assign new ones
    for code in permission_codes:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if perm:
            db.execute(role_permissions.insert().values(role_id=role_id, permission_id=perm.id))
    db.commit()
    return {"role_id": role_id, "permissions": permission_codes}


@router.put("/users/{user_id}/roles")
def assign_user_roles(
    user_id: int,
    role_ids: list[int],
    _u: User = Depends(require_permission("user.assign_role")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.execute(user_roles.delete().where(user_roles.c.user_id == user_id))
    for rid in role_ids:
        role = db.query(Role).filter(Role.id == rid).first()
        if role:
            db.execute(user_roles.insert().values(user_id=user_id, role_id=rid))
    db.commit()
    return {"user_id": user_id, "role_ids": role_ids}


# ── Permissions catalog ─────────────────────────────────────────────────────
@router.get("/permissions")
def list_permissions(_u: User = Depends(require_user), db: Session = Depends(get_db)):
    """Return all available permissions (for admin UI)."""
    perms = db.query(Permission).all()
    return [{"id": p.id, "code": p.code, "description": p.description} for p in perms]


# ── Password reset (admin-triggered) ────────────────────────────────────────
@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    new_password: str = None,
    _u: User = Depends(require_permission("user.reset_password")),
    db: Session = Depends(get_db),
):
    """Admin resets a user's password. If new_password is omitted, generates one."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    import secrets, string
    pwd = new_password or ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    user.password_hash = hash_password(pwd)
    db.commit()
    return {"username": user.username, "new_password": pwd if not new_password else "已重置为指定密码"}
