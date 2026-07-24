"""
Admin GUI routes — server-rendered management panel.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader
import pathlib, subprocess, sys

from app.database import get_db
from app.models import User
from app.auth import require_permission, get_current_user

TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "templates"
jinja = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)

router = APIRouter(prefix="/admin", tags=["admin"])


def render(template: str, user: User = None, **ctx) -> HTMLResponse:
    return HTMLResponse(jinja.get_template(template).render(current_user=user, **ctx))


# ── Login page ──────────────────────────────────────────────────────────────
@router.get("/login", response_class=HTMLResponse)
def admin_login_page():
    return HTMLResponse(jinja.get_template("admin/login.html").render())


# ── Dashboard ───────────────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard():
    """Client-side JS handles auth — renders dashboard shell, JS redirects to login if needed."""
    return render("admin/dashboard.html", page="dashboard")


# ── Books ───────────────────────────────────────────────────────────────────
@router.get("/books", response_class=HTMLResponse)
def admin_books():
    return render("admin/books.html", page="books")


# ── Users ───────────────────────────────────────────────────────────────────
@router.get("/users", response_class=HTMLResponse)
def admin_users():
    return render("admin/users.html", page="users")


# ── Catalog ─────────────────────────────────────────────────────────────────
@router.get("/catalog", response_class=HTMLResponse)
def admin_catalog():
    return render("admin/catalog.html", page="catalog")


# ── Stats ───────────────────────────────────────────────────────────────────
@router.get("/stats", response_class=HTMLResponse)
def admin_stats():
    return render("admin/stats.html", page="stats")


# ── Roles ───────────────────────────────────────────────────────────────────
@router.get("/roles", response_class=HTMLResponse)
def admin_roles():
    return render("admin/roles.html", page="roles")


# ── Book Upload ─────────────────────────────────────────────────────────────
@router.get("/book-upload", response_class=HTMLResponse)
def admin_book_upload():
    return render("admin/book_upload.html", page="book-upload")


# ── Asset Management ────────────────────────────────────────────────────────
@router.get("/assets", response_class=HTMLResponse)
def admin_assets():
    return render("admin/assets.html", page="assets")


@router.get("/articles", response_class=HTMLResponse)
def admin_articles():
    return render("admin/articles.html", page="articles")


@router.get("/article-editor", response_class=HTMLResponse)
def admin_article_editor():
    return render("admin/article_editor.html", page="article-editor")


@router.get("/issues", response_class=HTMLResponse)
def admin_issues():
    return render("admin/issues.html", page="issues")


@router.get("/elections", response_class=HTMLResponse)
def admin_elections():
    return render("admin/elections.html", page="elections")


@router.get("/quotes", response_class=HTMLResponse)
def admin_quotes():
    return render("admin/quotes.html", page="quotes")


@router.get("/settings", response_class=HTMLResponse)
def admin_settings():
    return render("admin/settings.html", page="settings")


@router.get("/invite-codes", response_class=HTMLResponse)
def admin_invite_codes():
    return render("admin/invite_codes.html", page="users")


# ── Rebuild endpoint ────────────────────────────────────────────────────────
@router.post("/rebuild")
def rebuild_site(_u: User = Depends(require_permission("book.publish"))):
    """Trigger a full static site rebuild."""
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "static_site.generator"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        from fastapi import HTTPException
        raise HTTPException(500, f"Build failed: {result.stderr[:500]}")
    return {"status": "ok", "lines": result.stdout.count("\n")}
