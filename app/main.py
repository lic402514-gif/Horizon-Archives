"""
Personal Library — FastAPI application entry point.
"""
import os, subprocess, pathlib, sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader

# Load .env
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.is_file():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import func as sa_func
from app.database import init_db, SessionLocal, get_db
from app.models import User, Book, DownloadLog, File, PageView
from app.auth import STORAGE_DIR, require_user
from app.routers import auth, books, downloads, uploads, admin as admin_router, rbac, assets, articles, register, activity, integration, comments, bookshelves, history, preview, dashboard, dedup, notifications, metadata, elections, issues, messages, quotes, settings

TEMPLATES = Environment(loader=FileSystemLoader("templates"), autoescape=True)
DIST_DIR = Path("dist")
STATIC_DIR = Path("static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Personal Library", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static-assets")

# ── Standalone routes (must be before routers to avoid {book_id} conflicts) ─

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(books.router)
app.include_router(downloads.router)
app.include_router(uploads.router)
app.include_router(admin_router.router)
app.include_router(rbac.router)
app.include_router(assets.router)
app.include_router(articles.router)
app.include_router(register.router)
app.include_router(activity.router)
app.include_router(issues.router)
app.include_router(elections.router)
app.include_router(quotes.router)
app.include_router(settings.router)
app.include_router(integration.router)
app.include_router(comments.router)
app.include_router(bookshelves.router)
app.include_router(history.router)
app.include_router(preview.router)
app.include_router(dashboard.router)
app.include_router(dedup.router)
app.include_router(notifications.router)
app.include_router(metadata.router)
app.include_router(messages.router)
# ── Standalone routes (avoid {book_id} conflicts) ──────────────────────────
@app.get("/api/auto-fill-book")
def auto_fill_book(isbn: str):
    """Auto-fill book metadata: Google Books → Tavily → DeepSeek memory."""
    import re
    from app.sources import auto_fill
    
    isbn = re.sub(r'[\s-]', '', isbn)
    if not re.match(r'^(97[89])?\d{9}[\dX]$', isbn):
        raise HTTPException(400, f"Invalid ISBN: {isbn}")
    
    try:
        return auto_fill(isbn)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Auto-fill failed: {str(e)}")


@app.get("/api/me")
def me(_r: Request, db: Session = Depends(get_db)):
    """Return current user info or null if not logged in."""
    token = _r.cookies.get("session")
    if not token:
        return {"username": None}
    try:
        from app.auth import get_current_user
        user = get_current_user(token=token, db=db)
        if user is None:
            return {"username": None}
        return {"username": user.username, "role": user.role, "id": user.id}
    except Exception:
        return {"username": None}


@app.get("/api/oss/sts")
def get_sts_token(_u: User = Depends(require_user)):
    """Return STS temporary credentials for OSS direct upload."""
    import json, hmac, hashlib, base64, time
    from app.auth import OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME, OSS_ENDPOINT

    if not all([OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME, OSS_ENDPOINT]):
        raise HTTPException(501, "OSS not configured")
    expire = int(time.time()) + 3600
    policy = json.dumps({
        "expiration": f"{time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(expire))}",
        "conditions": [
            {"bucket": OSS_BUCKET_NAME},
            ["starts-with", "$key", ""],
            {"success_action_status": "200"},
        ]
    })
    policy_b64 = base64.b64encode(policy.encode()).decode()
    signature = base64.b64encode(hmac.new(
        OSS_ACCESS_KEY_SECRET.encode(), policy_b64.encode(), hashlib.sha1
    ).digest()).decode()
    
    return {
        "endpoint": OSS_ENDPOINT.replace("https://","").replace("http://",""),
        "bucket": OSS_BUCKET_NAME,
        "access_key_id": OSS_ACCESS_KEY_ID,
        "policy": policy_b64,
        "signature": signature,
        "expire": expire
    }


@app.post("/api/assets/register")
def register_asset(body: dict, _u: User = Depends(require_user),
                   db: Session = Depends(get_db)):
    """Register an OSS-direct-uploaded file as an Asset record."""
    from app.models import Asset
    asset = Asset(
        filename=body["filename"], object_key=body["object_key"],
        size=body.get("size"), mime_type=body.get("mime_type"),
        asset_type=body.get("asset_type", "other"),
        provider="oss", bucket=body.get("bucket"))
    db.add(asset); db.commit(); db.refresh(asset)
    return {"id": asset.id, "filename": asset.filename, "object_key": asset.object_key}


@app.post("/api/rebuild-ssg")
def rebuild_ssg(_u: User = Depends(require_user)):
    """Trigger SSG rebuild after content changes."""
    from static_site.generator import build_all
    build_all()
    return {"status": "ok"}


@app.get("/api/image/{asset_id}")
def image_proxy(asset_id: int, w: int = 0, h: int = 0):
    """Public image proxy: generate pre-signed OSS URL -> 302 redirect.
    Optional w/h for OSS image resizing (e.g. /api/image/1?w=96&h=96)."""
    from app.auth import get_download_url
    from app.models import Asset
    from fastapi.responses import RedirectResponse
    db = SessionLocal()
    try:
        a = db.query(Asset).filter(Asset.id == asset_id).first()
        if not a: raise HTTPException(404)
        url = get_download_url(a.object_key, expires=3600)
        return RedirectResponse(url=url, status_code=302)
    finally:
        db.close()


# ── Public Pages ────────────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
def user_login_page():
    return HTMLResponse(TEMPLATES.get_template("user/login.html").render(now=datetime.now()))

@app.get("/register", response_class=HTMLResponse)
def user_register_page():
    return HTMLResponse(TEMPLATES.get_template("user/register.html").render(now=datetime.now()))

@app.get("/activity", response_class=HTMLResponse)
@app.get("/activity/{date:path}", response_class=HTMLResponse)
def activity_page(date: str = ""):
    db = SessionLocal()
    try:
        from app.models import Category
        from app.auth import get_current_user, cookie_scheme, oauth2_scheme
        from fastapi import Depends
        import asyncio
        categories = db.query(Category).filter((Category.parent_code == None) | (Category.parent_code == "")).order_by(Category.code).all()
        return HTMLResponse(TEMPLATES.get_template("activity.html").render(
            categories=categories, user=None, request_path="/activity"))
    finally:
        db.close()

# ── Stats ───────────────────────────────────────────────────────────────────
@app.get("/api/stats/summary")
def stats_summary():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        total = db.query(DownloadLog).count()
        today = db.query(DownloadLog).filter(DownloadLog.timestamp >= today_start).count()
        week = db.query(DownloadLog).filter(DownloadLog.timestamp >= week_start).count()
        month = db.query(DownloadLog).filter(DownloadLog.timestamp >= now - timedelta(days=30)).count()
        active = db.query(DownloadLog.user_id).filter(
            DownloadLog.timestamp >= now - timedelta(days=30),
            DownloadLog.user_id.isnot(None)
        ).distinct().count()
        recent = (db.query(DownloadLog).order_by(DownloadLog.timestamp.desc()).limit(10).all())
        recent_logs = []
        for rl in recent:
            book_title = None
            if rl.file_id:
                f = db.query(File).filter(File.id == rl.file_id).first()
                if f:
                    b = db.query(Book).filter(Book.id == f.book_id).first()
                    book_title = b.title if b else "-"
            user = db.query(User).filter(User.id == rl.user_id).first()
            recent_logs.append({
                "username": user.username if user else "-",
                "book_title": book_title or "-",
                "format": "-",
                "timestamp": rl.timestamp.isoformat() if rl.timestamp else "-"
            })
        return {"total_downloads": total, "today_downloads": today, "week_downloads": week, "month_downloads": month, "active_users": active, "recent_logs": recent_logs}
    finally:
        db.close()

@app.get("/api/stats/logs")
def stats_logs(limit: int = 100):
    db = SessionLocal()
    try:
        logs = db.query(DownloadLog).order_by(DownloadLog.timestamp.desc()).limit(limit).all()
        entries = []
        for l in logs:
            u = db.query(User).filter(User.id == l.user_id).first()
            f = db.query(File).filter(File.id == l.file_id).first() if l.file_id else None
            b = db.query(Book).filter(Book.id == f.book_id).first() if f else None
            entries.append({
                "id": l.id, "username": u.username if u else "-",
                "book_title": b.title if b else "-", "format": f.format if f else "-",
                "timestamp": l.timestamp.isoformat() if l.timestamp else "-"
            })
        return entries
    finally:
        db.close()

@app.post("/api/page-view")
def track_page_view(path: str = "/", request: Request = None, db: Session = Depends(get_db)):
    from sqlalchemy import func as sa_func
    from datetime import timezone as tz
    now = datetime.now(tz.utc).replace(tzinfo=None)
    ip = request.client.host if request else "127.0.0.1"
    session_key = request.cookies.get("session", "")[:64] if request else ""
    user_id = None
    # Try to resolve logged-in user from session
    if session_key:
        try:
            from app.auth import get_current_user
            user = get_current_user(token=session_key, db=db)
            if user: user_id = user.id
        except: pass
    
    existing = db.query(PageView).filter(
        PageView.page_path == path,
        PageView.session_key == session_key,
        PageView.last_viewed_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    ).first()
    if existing:
        existing.view_count += 1
        existing.last_viewed_at = now
    else:
        db.add(PageView(page_path=path, user_id=user_id, ip_address=ip,
                         session_key=session_key, view_count=1,
                         first_viewed_at=now, last_viewed_at=now))
    db.commit()
    return {"ok": True}

@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_static(path: str):
    if not path: path = "index.html"
    path = path.rstrip("/")
    fp = DIST_DIR / path
    if not fp.suffix:
        html = DIST_DIR / f"{path}.html"
        if html.is_file(): fp = html
        else: fp = DIST_DIR / f"{path}/index.html"
    if fp.is_file() and fp.suffix == ".html":
        return HTMLResponse(fp.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>404 Not Found</h1>", status_code=404)
