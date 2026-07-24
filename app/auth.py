"""
JWT auth utilities + OSS storage abstraction.
"""
import os
import hashlib
import bcrypt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Role

# ── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

# ── Password hashing ────────────────────────────────────────────────────────
from fastapi.security import APIKeyCookie

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)
cookie_scheme = APIKeyCookie(name="session", auto_error=False)


def hash_password(plain: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, token_version: int = 1) -> str:
    to_encode = data.copy()
    to_encode["ver"] = token_version
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    cookie: str | None = Depends(cookie_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Returns the authenticated user, or None if no valid token.
    Checks cookie first, then Authorization header, then ?token= query param (handled by caller)."""
    token = cookie or token  # cookie takes priority
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        return None
    from sqlalchemy.orm import joinedload
    user = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.id == user_id)
        .first()
    )
    if user is None or user.status != "ACTIVE":
        return None
    # Verify token_version — kicks out old sessions if user logged in elsewhere
    if payload.get("ver", 1) != (user.token_version or 1):
        return None
    return user


def require_user(current_user: User | None = Depends(get_current_user)) -> User:
    """Dependency: raises 401 if not authenticated."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return current_user


def require_permission(code: str):
    """Factory: returns a FastAPI dependency that checks a specific permission."""
    def checker(current_user: User = Depends(require_user)) -> User:
        if not current_user.has_permission(code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Missing permission: {code}")
        return current_user
    return checker


def require_admin(current_user: User = Depends(require_user)) -> User:
    """Legacy: full admin check. Use require_permission for granular checks."""
    if current_user.has_permission("system.config"):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")


# ── Operation logging ───────────────────────────────────────────────────────
def op_log(
    db: Session,
    user: User,
    action: str,
    target_type: str = None,
    target_id: str = None,
    detail: str = None,
    ip_address: str = None,
    result: str = "success",
):
    """Record an operation to the audit log."""
    from app.models import OperationLog as OL
    log = OL(
        user_id=user.id if user else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        detail=detail,
        ip_address=ip_address,
        result=result,
    )
    db.add(log)
    db.flush()


# ── RBAC Permission System ──────────────────────────────────────────────────

def _get_user_permissions(db: Session, user: User) -> set[str]:
    """Return set of permission codes for a user."""
    from app.models import Permission, user_roles, role_permissions
    # Legacy: admin role gets all permissions
    if user.role == "admin":
        perms = db.query(Permission.code).all()
        return {p[0] for p in perms}
    # RBAC: collect permissions via user_roles → role_permissions → permissions
    perm_tuples = (
        db.query(Permission.code)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .join(user_roles, user_roles.c.role_id == role_permissions.c.role_id)
        .filter(user_roles.c.user_id == user.id)
        .all()
    )
    return {p[0] for p in perm_tuples}


def has_permission(user: User, db: Session, code: str) -> bool:
    """Check if user has a specific permission."""
    return code in _get_user_permissions(db, user)


def require_permission(code: str):
    """FastAPI dependency factory: returns a dependency that checks `code` permission."""
    def checker(current_user: User = Depends(require_user), db: Session = Depends(get_db)) -> User:
        if not has_permission(current_user, db, code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {code}")
        return current_user
    return checker


# ── Operation Logging ───────────────────────────────────────────────────────

def oplog(db: Session, user: User, action: str, target_type: str = None,
          target_id: str = None, detail: str = None, ip: str = None, result: str = "success"):
    """Write an operation log entry."""
    from app.models import OperationLog
    log = OperationLog(
        user_id=user.id if user else None,
        action=action, target_type=target_type,
        target_id=str(target_id) if target_id else None,
        detail=detail, ip_address=ip, result=result,
    )
    db.add(log)
    db.commit()


# ── Storage abstraction (local filesystem / OSS) ─────────────────────────────
STORAGE_DIR = os.getenv("STORAGE_DIR", "./data/files")
os.makedirs(STORAGE_DIR, exist_ok=True)

# OSS config — if all set, OSS mode is enabled
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "")
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "")
OSS_ENABLED = all([OSS_ENDPOINT, OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME])

_oss_bucket = None


def _get_bucket():
    """Lazy-init OSS bucket."""
    global _oss_bucket
    if _oss_bucket is None and OSS_ENABLED:
        import oss2
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        _oss_bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    return _oss_bucket


def generate_oss_key(book_id: int, format: str, filename: str) -> str:
    """Generate a unique OSS object key."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
    return f"books/{book_id}/{timestamp}_{safe_name}.{format}"


def get_download_url(oss_key: str, expires: int = 300, provider: str = "oss") -> str:
    """
    Return a download URL:
    - OSS mode: pre-signed GET URL (only if provider='oss')
    - Local mode: /static-files/ path served by FastAPI
    """
    if OSS_ENABLED and provider == "oss":
        bucket = _get_bucket()
        return bucket.sign_url("GET", oss_key, expires)
    return f"/static-files/{oss_key}"


def delete_oss_object(oss_key: str) -> bool:
    """Delete an object from OSS. Returns True on success."""
    if not oss_key: return False
    try:
        if OSS_ENABLED:
            _get_bucket().delete_object(oss_key)
        else:
            path = STORAGE_DIR / oss_key
            if path.exists(): path.unlink()
        return True
    except Exception:
        return False


def get_upload_url(oss_key: str, expires: int = 3600) -> str | None:
    """
    Return a pre-signed upload URL (OSS mode only).
    Returns None in local mode (upload handled by /api/upload-file directly).
    """
    if OSS_ENABLED:
        bucket = _get_bucket()
        return bucket.sign_url("PUT", oss_key, expires)
    return None
