"""
Article CMS v2 — full FrontMatter, versions, publish with SSG.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import re, markdown

from app.database import get_db
from app.models import Article, ArticleVersion, User
from app.auth import require_permission, require_user

router = APIRouter(prefix="/api", tags=["articles"])


def _article_dict(a: Article) -> dict:
    return {
        "id": a.id, "slug": a.slug, "title": a.title, "summary": a.summary,
        "author_name": a.author_name, "status": a.status,
        "category": a.category, "tags": a.tags.split(",") if a.tags else [],
        "content_md": a.content_md, "content_html": a.content_html,
        "seo_title": a.seo_title, "seo_description": a.seo_description,
        "seo_keywords": a.seo_keywords, "canonical_url": a.canonical_url,
        "reading_time": a.reading_time, "word_count": a.word_count,
        "version": a.version, "cover_asset_id": a.cover_asset_id,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("/articles")
def list_articles(status: str = None, tag: str = None, category: str = None,
                  _u: User = Depends(require_user), db: Session = Depends(get_db)):
    q = db.query(Article)
    if status: q = q.filter(Article.status == status)
    if category: q = q.filter(Article.category == category)
    if tag: q = q.filter(Article.tags.contains(tag))
    return [_article_dict(a) for a in q.order_by(Article.updated_at.desc()).all()]


@router.get("/articles/{ident}")
def get_article(ident: str, db: Session = Depends(get_db)):
    a = db.query(Article).filter(
        (Article.id == int(ident)) if ident.isdigit() else (Article.slug == ident)
    ).first()
    if not a: raise HTTPException(404, "Article not found")
    return _article_dict(a)


@router.post("/articles", status_code=201)
def create_article(body: dict, _u: User = Depends(require_permission("article.create")),
                   db: Session = Depends(get_db)):
    slug = body.get("slug") or re.sub(r"[^\w-]", "", body.get("title", "")).lower()[:80]
    if not slug: slug = f"article-{int(datetime.now(timezone.utc).timestamp())}"
    if db.query(Article).filter(Article.slug == slug).first():
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"

    content_md = body.get("content_md", "")
    wc = len(content_md.replace(" ", "")) if content_md else 0
    rt = max(1, wc // 300) if wc else 1

    a = Article(
        slug=slug, title=body["title"], author_name=body.get("author_name"),
        summary=body.get("summary"), content_md=content_md,
        category=body.get("category"),
        tags=",".join(body["tags"]) if isinstance(body.get("tags"), list) else body.get("tags"),
        seo_title=body.get("seo_title"), seo_description=body.get("seo_description"),
        seo_keywords=body.get("seo_keywords"),
        status=body.get("status", "draft"), reading_time=rt, word_count=wc,
    )
    db.add(a); db.commit(); db.refresh(a)
    return _article_dict(a)


@router.put("/articles/{article_id}")
def update_article(article_id: int, body: dict,
                   _u: User = Depends(require_permission("article.create")),
                   db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a: raise HTTPException(404, "Article not found")

    # Save current version before overwriting
    ov = ArticleVersion(article_id=a.id, version_number=a.version,
                        content_md=a.content_md, content_html=a.content_html,
                        editor_id=_u.id, summary_changes=body.get("change_summary"))
    db.add(ov)

    # Update fields
    for k in ["title", "summary", "author_name", "content_md", "category",
              "seo_title", "seo_description", "seo_keywords", "status"]:
        if k in body: setattr(a, k, body[k])
    if "tags" in body:
        a.tags = ",".join(body["tags"]) if isinstance(body["tags"], list) else body["tags"]
    if "slug" in body and body["slug"] != a.slug:
        if db.query(Article).filter(Article.slug == body["slug"], Article.id != article_id).first():
            raise HTTPException(400, "Slug already taken")
        a.slug = body["slug"]

    content_md = a.content_md or ""
    a.word_count = len(content_md.replace(" ", ""))
    a.reading_time = max(1, a.word_count // 300)
    a.version += 1
    a.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(a)
    return _article_dict(a)


@router.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int, _u: User = Depends(require_permission("article.create")),
                   db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a: raise HTTPException(404, "Article not found")
    # Clean OSS images referenced in markdown
    from app.auth import delete_oss_object
    from app.models import ArticleAsset, Asset
    for aa in db.query(ArticleAsset).filter(ArticleAsset.article_id == article_id).all():
        asset = db.query(Asset).filter(Asset.id == aa.asset_id).first()
        if asset and asset.object_key:
            delete_oss_object(asset.object_key)
        db.delete(aa)
    # Delete HTML from dist/
    from pathlib import Path
    html = Path("dist/articles") / f"{a.slug}.html"
    if html.exists(): html.unlink()
    db.delete(a); db.commit()


# ── Versions ────────────────────────────────────────────────────────────────

@router.get("/articles/{article_id}/versions")
def list_versions(article_id: int, _u: User = Depends(require_user),
                  db: Session = Depends(get_db)):
    vs = db.query(ArticleVersion).filter(ArticleVersion.article_id == article_id)\
           .order_by(ArticleVersion.version_number.desc()).all()
    return [{"id": v.id, "version": v.version_number, "editor_id": v.editor_id,
             "summary": v.summary_changes, "created_at": v.created_at.isoformat()} for v in vs]


@router.get("/articles/{article_id}/versions/{vid}")
def get_version(article_id: int, vid: int, _u: User = Depends(require_user),
                db: Session = Depends(get_db)):
    v = db.query(ArticleVersion).filter(
        ArticleVersion.id == vid, ArticleVersion.article_id == article_id).first()
    if not v: raise HTTPException(404, "Version not found")
    return {"id": v.id, "version": v.version_number, "content_md": v.content_md,
            "summary": v.summary_changes}


@router.post("/articles/{article_id}/versions/{vid}/restore")
def restore_version(article_id: int, vid: int,
                    _u: User = Depends(require_permission("article.create")),
                    db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    v = db.query(ArticleVersion).filter(ArticleVersion.id == vid, ArticleVersion.article_id == article_id).first()
    if not a or not v: raise HTTPException(404, "Not found")
    # Save current as version before restoring
    db.add(ArticleVersion(article_id=a.id, version_number=a.version,
                          content_md=a.content_md, content_html=a.content_html,
                          editor_id=_u.id, summary_changes=f"Restored from v{v.version_number}"))
    a.content_md = v.content_md
    a.content_html = v.content_html
    a.version += 1; a.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "restored", "version": a.version}


# ── Publish ─────────────────────────────────────────────────────────────────

@router.post("/articles/{article_id}/publish")
def publish_article(article_id: int, _u: User = Depends(require_permission("article.publish")),
                    db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a: raise HTTPException(404, "Article not found")
    if not a.content_md: raise HTTPException(400, "No markdown content")

    import markdown
    try:
        html_body = markdown.markdown(a.content_md, extensions=["extra", "codehilite"])
        from app.sanitize import sanitize_html
        html_body = sanitize_html(html_body)
    except Exception:
        html_body = f"<pre>{a.content_md}</pre>"

    a.content_html = html_body  # body only, template wraps it in SSG
    a.status = "published"
    a.published_at = datetime.now(timezone.utc)
    a.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Write article page directly to dist/
    from pathlib import Path as PPath
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("static_site/templates"))
    tmpl = env.get_template("article.html")
    ad = PPath("dist/articles")
    ad.mkdir(parents=True, exist_ok=True)
    (ad / f"{a.slug}.html").write_text(
        tmpl.render(article=a, title=f"{a.title} — 个人图书馆资源小站", base_path=".."),
        encoding="utf-8"
    )

    return {"status": "published", "slug": a.slug, "url": f"/articles/{a.slug}.html"}
