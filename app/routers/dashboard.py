"""
Enhanced dashboard statistics API.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as sa_func, text, distinct

from app.database import get_db
from app.models import Book, User, DownloadLog, PageView, OperationLog

router = APIRouter(prefix="/api/stats", tags=["dashboard"])


@router.get("/dashboard")
def dashboard_stats(db=Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Book counts
    total_books = db.query(sa_func.count(Book.id)).scalar() or 0
    published_books = db.query(sa_func.count(Book.id)).filter(Book.status == "published").scalar() or 0
    draft_books = db.query(sa_func.count(Book.id)).filter(Book.status == "draft").scalar() or 0

    # User counts
    total_users = db.query(sa_func.count(User.id)).scalar() or 0
    active_users = db.query(sa_func.count(User.id)).filter(User.status == "ACTIVE").scalar() or 0

    # Download stats
    total_downloads = db.query(sa_func.count(DownloadLog.id)).scalar() or 0
    today_downloads = db.query(sa_func.count(DownloadLog.id)).filter(
        DownloadLog.timestamp >= today_start
    ).scalar() or 0

    # Page view stats
    total_views = db.query(sa_func.sum(PageView.view_count)).scalar() or 0
    today_ips = db.query(sa_func.count(distinct(PageView.ip_address))).filter(
        PageView.last_viewed_at >= today_start
    ).scalar() or 0

    # Daily download trend (last 30 days)
    daily_trend = []
    for i in range(29, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(sa_func.count(DownloadLog.id)).filter(
            DownloadLog.timestamp >= day_start,
            DownloadLog.timestamp < day_end,
        ).scalar() or 0
        daily_trend.append({
            "date": day_start.strftime("%m-%d"),
            "count": count,
        })

    # Top 10 books by downloads (all time)
    top_books = []
    from app.models import File as BookFile
    top_downloads = (
        db.query(DownloadLog.file_id, sa_func.count(DownloadLog.id).label("cnt"))
        .group_by(DownloadLog.file_id)
        .order_by(text("cnt DESC"))
        .limit(10)
        .all()
    )
    for file_id, cnt in top_downloads:
        f = db.query(BookFile).filter(BookFile.id == file_id).first()
        if f:
            b = db.query(Book).filter(Book.id == f.book_id).first()
            if b:
                top_books.append({"title": b.title, "count": cnt})

    # User growth (last 30 days, cumulative)
    user_growth = []
    cumulative = db.query(sa_func.count(User.id)).filter(
        User.created_at < (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    ).scalar() or 0
    for i in range(29, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        new_users = db.query(sa_func.count(User.id)).filter(
            User.created_at >= day_start,
            User.created_at < day_end,
        ).scalar() or 0
        cumulative += new_users
        user_growth.append({
            "date": day_start.strftime("%m-%d"),
            "count": cumulative,
        })

    return {
        "total_books": total_books,
        "published_books": published_books,
        "draft_books": draft_books,
        "total_users": total_users,
        "active_users": active_users,
        "total_downloads": total_downloads,
        "today_downloads": today_downloads,
        "total_views": total_views,
        "today_ips": today_ips,
        "daily_trend": daily_trend,
        "top_books": top_books,
        "user_growth": user_growth,
    }
