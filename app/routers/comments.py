"""
Book and Article comments API.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.auth import require_user, require_permission
from app.models import User, BookComment, ArticleComment

router = APIRouter(prefix="/api", tags=["comments"])


def _comment_out(comment, avatar_url=None):
    return {
        "id": comment.id,
        "book_id": getattr(comment, "book_id", None),
        "article_id": getattr(comment, "article_id", None),
        "user_id": comment.user_id,
        "username": comment.user.username if comment.user else "",
        "avatar_url": comment.user.avatar.url if (comment.user and comment.user.avatar) else None,
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
    }


# ── Book Comments ──────────────────────────────────────────────────────────

@router.get("/books/{book_id}/comments")
def list_book_comments(
    book_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db=Depends(get_db),
):
    q = (
        db.query(BookComment)
        .options(joinedload(BookComment.user))
        .filter(BookComment.book_id == book_id)
        .order_by(BookComment.created_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "rows": [_comment_out(c) for c in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/books/{book_id}/comments", status_code=201)
def create_book_comment(
    book_id: int,
    body: dict,
    request: Request,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="评论内容不能超过2000字")

    comment = BookComment(
        book_id=book_id,
        user_id=current_user.id,
        content=content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    # reload with user
    comment = db.query(BookComment).options(joinedload(BookComment.user)).filter(BookComment.id == comment.id).first()
    return _comment_out(comment)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_book_comment(
    comment_id: int,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    comment = db.query(BookComment).filter(BookComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.user_id != current_user.id and not current_user.has_permission("comment.delete"):
        raise HTTPException(status_code=403, detail="无权删除此评论")
    db.delete(comment)
    db.commit()


# ── Article Comments ───────────────────────────────────────────────────────

@router.get("/articles/{article_id}/comments")
def list_article_comments(
    article_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    db=Depends(get_db),
):
    q = (
        db.query(ArticleComment)
        .options(joinedload(ArticleComment.user))
        .filter(ArticleComment.article_id == article_id)
        .order_by(ArticleComment.created_at.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "rows": [_comment_out(c) for c in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/articles/{article_id}/comments", status_code=201)
def create_article_comment(
    article_id: int,
    body: dict,
    request: Request,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="评论内容不能超过2000字")

    comment = ArticleComment(
        article_id=article_id,
        user_id=current_user.id,
        content=content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment = db.query(ArticleComment).options(joinedload(ArticleComment.user)).filter(ArticleComment.id == comment.id).first()
    return _comment_out(comment)


@router.delete("/article-comments/{comment_id}", status_code=204)
def delete_article_comment(
    comment_id: int,
    current_user: User = Depends(require_user),
    db=Depends(get_db),
):
    comment = db.query(ArticleComment).filter(ArticleComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.user_id != current_user.id and not current_user.has_permission("comment.delete"):
        raise HTTPException(status_code=403, detail="无权删除此评论")
    db.delete(comment)
    db.commit()
