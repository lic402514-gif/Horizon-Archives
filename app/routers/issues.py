"""Issue governance API — CRUD, voting, comments, results."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Issue, IssueOption, Vote, IssueComment, IssueResult, User
from app.auth import require_user, require_permission, oplog

router = APIRouter(prefix="/api", tags=["issues"])

def _issue_dict(i):
    return {"id": i.id, "title": i.title, "slug": i.slug, "content": i.content,
            "content_html": i.content_html, "summary": i.summary, "creator_id": i.creator_id,
            "status": i.status, "vote_type": i.vote_type,
            "discussion_start": i.discussion_start.isoformat() if i.discussion_start else None,
            "discussion_end": i.discussion_end.isoformat() if i.discussion_end else None,
            "vote_start": i.vote_start.isoformat() if i.vote_start else None,
            "vote_end": i.vote_end.isoformat() if i.vote_end else None,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "updated_at": i.updated_at.isoformat() if i.updated_at else None,
            "options": [{"id": o.id, "title": o.title, "content": o.content, "sort": o.sort, "vote_count": o.vote_count}
                        for o in (i.options or [])],
            "creator": i.creator.username if i.creator else None,
            "comment_count": len(i.comments) if i.comments else 0,
            "vote_count_total": len(i.votes) if i.votes else 0,
            }

# ── CRUD ─────────────────────────────────────────────────────────────────

@router.get("/issues")
def list_issues(status: str = None, db: Session = Depends(get_db)):
    q = db.query(Issue)
    if status: q = q.filter(Issue.status == status)
    return [_issue_dict(i) for i in q.order_by(Issue.created_at.desc()).all()]

@router.post("/issues", status_code=201)
def create_issue(body: dict, _u: User = Depends(require_permission("issue.create")),
                 db: Session = Depends(get_db)):
    import re
    slug = body.get("slug") or re.sub(r"[^\w]+", "-", body["title"]).strip("-").lower() or "issue"
    i = Issue(title=body["title"], slug=slug, content=body.get("content"), summary=body.get("summary"),
              creator_id=_u.id, status="draft", vote_type=body.get("vote_type", "simple_majority"))
    db.add(i); db.commit(); db.refresh(i)
    # Add options if provided
    for opt in body.get("options") or []:
        o = IssueOption(issue_id=i.id, title=opt["title"], content=opt.get("content"), sort=opt.get("sort", 0))
        db.add(o)
    db.commit()
    oplog(db, _u, "issue.create", "issue", str(i.id))
    return _issue_dict(i)

@router.get("/issues/{ident}")
def get_issue(ident: str, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    i = db.query(Issue).options(
        joinedload(Issue.options), joinedload(Issue.comments).joinedload(IssueComment.user)
    ).filter((Issue.id == int(ident)) if ident.isdigit() else (Issue.slug == ident)).first()
    if not i: raise HTTPException(404)
    return _issue_dict(i)

@router.put("/issues/{issue_id}")
def update_issue(issue_id: int, body: dict, _u: User = Depends(require_permission("issue.create")),
                 db: Session = Depends(get_db)):
    i = db.query(Issue).filter(Issue.id == issue_id).first()
    if not i: raise HTTPException(404)
    for k in ["title", "content", "summary", "status", "vote_type", "discussion_end", "vote_start", "vote_end", "slug"]:
        if k in body: setattr(i, k, body[k])
    if "content" in body:
        import markdown
        i.content_html = markdown.markdown(body["content"], extensions=["extra", "codehilite"])
        from app.sanitize import sanitize_html
        i.content_html = sanitize_html(i.content_html)
    db.commit(); oplog(db, _u, "issue.update", "issue", str(i.id))
    return _issue_dict(i)

@router.delete("/issues/{issue_id}")
def delete_issue(issue_id: int, _u: User = Depends(require_permission("issue.create")),
                 db: Session = Depends(get_db)):
    i = db.query(Issue).filter(Issue.id == issue_id).first()
    if not i: raise HTTPException(404)
    db.delete(i); db.commit(); oplog(db, _u, "issue.delete", "issue", str(issue_id))
    return {"deleted": True}

# ── Options ──────────────────────────────────────────────────────────────

@router.post("/issues/{issue_id}/options", status_code=201)
def add_option(issue_id: int, body: dict, _u: User = Depends(require_permission("issue.create")),
               db: Session = Depends(get_db)):
    o = IssueOption(issue_id=issue_id, title=body["title"], content=body.get("content"), sort=body.get("sort", 0))
    db.add(o); db.commit(); db.refresh(o)
    return {"id": o.id, "title": o.title, "content": o.content}

@router.put("/issues/{issue_id}/options/{option_id}")
def update_option(issue_id: int, option_id: int, body: dict,
                  _u: User = Depends(require_permission("issue.create")), db: Session = Depends(get_db)):
    o = db.query(IssueOption).filter(IssueOption.id == option_id, IssueOption.issue_id == issue_id).first()
    if not o: raise HTTPException(404)
    for k in ["title", "content", "sort"]:
        if k in body: setattr(o, k, body[k])
    db.commit()
    return {"id": o.id, "title": o.title}

@router.delete("/issues/{issue_id}/options/{option_id}")
def delete_option(issue_id: int, option_id: int, _u: User = Depends(require_permission("issue.create")),
                  db: Session = Depends(get_db)):
    db.query(IssueOption).filter(IssueOption.id == option_id, IssueOption.issue_id == issue_id).delete()
    db.commit()
    return {"deleted": True}

# ── Voting ───────────────────────────────────────────────────────────────

@router.post("/issues/{issue_id}/vote")
def cast_vote(issue_id: int, body: dict, _u: User = Depends(require_permission("issue.vote")), db: Session = Depends(get_db)):
    i = db.query(Issue).filter(Issue.id == issue_id).first()
    if not i: raise HTTPException(404)
    if i.status != "voting": raise HTTPException(400, "Issue not in voting phase")
    from datetime import datetime as dt, timezone
    if i.vote_end and dt.now(timezone.utc).replace(tzinfo=None) > i.vote_end: raise HTTPException(400, "Voting has ended")

    if i.vote_type == "approval":
        # Multi-select: body.option_ids = [1,2,3]
        oids = body.get("option_ids") or [body.get("option_id")]
        existing = db.query(Vote).filter(Vote.issue_id == issue_id, Vote.user_id == _u.id).all()
        for ev in existing: db.delete(ev)
        for oid in oids:
            db.add(Vote(issue_id=issue_id, option_id=oid, user_id=_u.id))
            db.query(IssueOption).filter(IssueOption.id == oid).update({"vote_count": IssueOption.vote_count + 1})
    else:
        # Single choice: body.option_id = 1
        oid = body["option_id"]
        existing = db.query(Vote).filter(Vote.issue_id == issue_id, Vote.user_id == _u.id).first()
        if existing:
            # Update vote
            old_oid = existing.option_id
            db.query(IssueOption).filter(IssueOption.id == old_oid).update({"vote_count": IssueOption.vote_count - 1})
            existing.option_id = oid
        else:
            db.add(Vote(issue_id=issue_id, option_id=oid, user_id=_u.id))
        db.query(IssueOption).filter(IssueOption.id == oid).update({"vote_count": IssueOption.vote_count + 1})
    db.commit()
    return {"status": "voted"}

@router.get("/issues/{issue_id}/my-vote")
def my_vote(issue_id: int, _u: User = Depends(require_permission("issue.read")), db: Session = Depends(get_db)):
    votes = db.query(Vote).filter(Vote.issue_id == issue_id, Vote.user_id == _u.id).all()
    return {"option_ids": [v.option_id for v in votes]}

# ── Comments ─────────────────────────────────────────────────────────────

@router.get("/issues/{issue_id}/comments")
def list_comments(issue_id: int, db: Session = Depends(get_db)):
    comments = db.query(IssueComment).filter(IssueComment.issue_id == issue_id, IssueComment.status == "approved").order_by(IssueComment.created_at).all()
    return [{"id": c.id, "user": c.user.username if c.user else "?", "content": c.content,
             "parent_id": c.parent_id, "created_at": c.created_at.isoformat() if c.created_at else None,
             "replies": []} for c in comments]

@router.post("/issues/{issue_id}/comments", status_code=201)
def add_comment(issue_id: int, body: dict, _u: User = Depends(require_permission("issue.comment")), db: Session = Depends(get_db)):
    c = IssueComment(issue_id=issue_id, user_id=_u.id, parent_id=body.get("parent_id"),
                     content=body["content"], status="approved")
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "content": c.content, "user": _u.username, "created_at": c.created_at.isoformat()}

@router.delete("/issues/{issue_id}/comments/{comment_id}")
def delete_comment(issue_id: int, comment_id: int, _u: User = Depends(require_permission("issue.comment")), db: Session = Depends(get_db)):
    c = db.query(IssueComment).filter(IssueComment.id == comment_id).first()
    if not c or c.user_id != _u.id: raise HTTPException(403)
    c.status = "deleted"; db.commit()
    return {"deleted": True}

# ── Results ──────────────────────────────────────────────────────────────

def _calculate_result(issue: Issue, db: Session):
    options = issue.options
    if issue.vote_type == "simple_majority":
        total = sum(o.vote_count for o in options) or 1
        for o in options:
            pct = round(o.vote_count / total * 100, 1) if total else 0
            db.merge(IssueResult(issue_id=issue.id, option_id=o.id, vote_count=o.vote_count, percentage=pct, rank=0))
        # Rank
        results = list(reversed(sorted(enumerate(options), key=lambda x: x[1].vote_count)))
        for rank, (_, o) in enumerate(results, 1):
            db.query(IssueResult).filter(IssueResult.issue_id == issue.id, IssueResult.option_id == o.id).update({"rank": rank})
    elif issue.vote_type == "absolute_majority":
        total = sum(o.vote_count for o in options) or 1
        for o in options:
            pct = round(o.vote_count / total * 100, 1)
            rank = 1 if pct > 50 else 0
            db.merge(IssueResult(issue_id=issue.id, option_id=o.id, vote_count=o.vote_count, percentage=pct, rank=rank))
    elif issue.vote_type == "approval":
        total_users = db.query(Vote.user_id).filter(Vote.issue_id == issue.id).distinct().count() or 1
        for o in options:
            pct = round(o.vote_count / total_users * 100, 1)
            db.merge(IssueResult(issue_id=issue.id, option_id=o.id, vote_count=o.vote_count, percentage=pct, rank=0))
        results = list(reversed(sorted(enumerate(options), key=lambda x: x[1].vote_count)))
        for rank, (_, o) in enumerate(results, 1):
            db.query(IssueResult).filter(IssueResult.issue_id == issue.id, IssueResult.option_id == o.id).update({"rank": rank})
    db.commit()

@router.post("/issues/{issue_id}/calculate")
def calculate_result(issue_id: int, _u: User = Depends(require_permission("issue.create")),
                     db: Session = Depends(get_db)):
    i = db.query(Issue).options(__import__("sqlalchemy.orm").joinedload(Issue.options)).filter(Issue.id == issue_id).first()
    if not i: raise HTTPException(404)
    _calculate_result(i, db)
    i.status = "finished"; db.commit()
    oplog(db, _u, "issue.result", "issue", str(i.id))
    return _issue_dict(i)

@router.get("/issues/{issue_id}/result")
def get_result(issue_id: int, db: Session = Depends(get_db)):
    results = db.query(IssueResult).filter(IssueResult.issue_id == issue_id).order_by(IssueResult.rank).all()
    return [{"option_id": r.option_id, "vote_count": r.vote_count, "percentage": r.percentage, "rank": r.rank,
             "option_title": r.option.title if r.option else ""} for r in results]
