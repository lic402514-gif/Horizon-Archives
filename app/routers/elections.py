"""Election API — CRUD, candidates, voting, results."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Election, ElectionCandidate, ElectionVote, ElectionResult, User
from app.auth import require_user, require_permission, oplog

router = APIRouter(prefix="/api", tags=["elections"])

def _e_dict(e):
    return {"id":e.id,"title":e.title,"slug":e.slug,"description":e.description,
            "content":e.content,"content_html":e.content_html,"position":e.position,
            "seats":e.seats,"status":e.status,"vote_type":e.vote_type,
            "creator":e.creator.username if e.creator else None,
            "nomination_start":e.nomination_start.isoformat() if e.nomination_start else None,
            "nomination_end":e.nomination_end.isoformat() if e.nomination_end else None,
            "voting_start":e.voting_start.isoformat() if e.voting_start else None,
            "voting_end":e.voting_end.isoformat() if e.voting_end else None,
            "created_at":e.created_at.isoformat() if e.created_at else None,
            "candidates":[{"id":c.id,"user_id":c.user_id,"name":c.user.username if c.user else "?",
                           "biography":c.biography,"manifesto":c.manifesto,"status":c.status,
                           "vote_count":c.vote_count} for c in (e.candidates or [])]}

# ── CRUD ─────────────────────────────────────────────────────────────────

@router.get("/elections")
def list_elections(status: str = None, db: Session = Depends(get_db)):
    q = db.query(Election)
    if status: q = q.filter(Election.status == status)
    return [_e_dict(e) for e in q.order_by(Election.created_at.desc()).all()]

@router.post("/elections", status_code=201)
def create_election(body: dict, _u: User = Depends(require_permission("election.create")),
                    db: Session = Depends(get_db)):
    import re
    slug = body.get("slug") or re.sub(r"[^\w]+","-",body["title"]).strip("-").lower() or "election"
    e = Election(title=body["title"],slug=slug,description=body.get("description"),
                 content=body.get("content"),position=body.get("position"),
                 seats=body.get("seats",1),vote_type=body.get("vote_type","simple_majority"),
                 creator_id=_u.id,status="draft")
    db.add(e); db.commit(); db.refresh(e)
    oplog(db,_u,"election.create","election",str(e.id))
    return _e_dict(e)

@router.get("/elections/{ident}")
def get_election(ident: str, db: Session = Depends(get_db)):
    e = db.query(Election).filter(
        (Election.id == int(ident)) if ident.isdigit() else (Election.slug == ident)
    ).first()
    if not e: raise HTTPException(404)
    return _e_dict(e)

@router.put("/elections/{election_id}")
def update_election(election_id: int, body: dict,
                    _u: User = Depends(require_permission("election.create")),
                    db: Session = Depends(get_db)):
    e = db.query(Election).filter(Election.id == election_id).first()
    if not e: raise HTTPException(404)
    for k in ["title","slug","description","content","position","seats","vote_type","status",
              "nomination_start","nomination_end","voting_start","voting_end"]:
        if k in body: setattr(e, k, body[k])
    if "content" in body:
        import markdown
        e.content_html = markdown.markdown(body["content"], extensions=["extra","codehilite"])
        from app.sanitize import sanitize_html
        e.content_html = sanitize_html(e.content_html)
    db.commit(); oplog(db,_u,"election.update","election",str(e.id))
    return _e_dict(e)

@router.delete("/elections/{election_id}")
def delete_election(election_id: int, _u: User = Depends(require_permission("election.create")),
                    db: Session = Depends(get_db)):
    e = db.query(Election).filter(Election.id == election_id).first()
    if not e: raise HTTPException(404)
    db.delete(e); db.commit()
    return {"deleted":True}

# ── Candidates ───────────────────────────────────────────────────────────

@router.post("/elections/{election_id}/candidates", status_code=201)
def nominate(election_id: int, body: dict, _u: User = Depends(require_permission("election.vote")),
             db: Session = Depends(get_db)):
    e = db.query(Election).filter(Election.id == election_id).first()
    if not e or e.status != "nomination": raise HTTPException(400,"Not in nomination phase")
    c = ElectionCandidate(election_id=election_id, user_id=_u.id,
                          biography=body.get("biography"), manifesto=body.get("manifesto"),
                          status="approved")
    db.add(c); db.commit(); db.refresh(c)
    return {"id":c.id,"status":c.status}

@router.put("/elections/{election_id}/candidates/{candidate_id}")
def review_candidate(election_id: int, candidate_id: int, body: dict,
                     _u: User = Depends(require_permission("election.create")),
                     db: Session = Depends(get_db)):
    c = db.query(ElectionCandidate).filter(
        ElectionCandidate.id == candidate_id, ElectionCandidate.election_id == election_id
    ).first()
    if not c: raise HTTPException(404)
    for k in ["status","biography","manifesto"]:
        if k in body: setattr(c,k,body[k])
    db.commit()
    return {"id":c.id,"status":c.status}

@router.delete("/elections/{election_id}/candidates/{candidate_id}")
def remove_candidate(election_id: int, candidate_id: int,
                     _u: User = Depends(require_permission("election.create")),
                     db: Session = Depends(get_db)):
    db.query(ElectionCandidate).filter(
        ElectionCandidate.id == candidate_id, ElectionCandidate.election_id == election_id
    ).delete()
    db.commit()
    return {"deleted":True}

# ── Voting ───────────────────────────────────────────────────────────────

@router.post("/elections/{election_id}/vote")
def cast_election_vote(election_id: int, body: dict,
                       _u: User = Depends(require_permission("election.vote")),
                       db: Session = Depends(get_db)):
    e = db.query(Election).filter(Election.id == election_id).first()
    if not e or e.status != "voting": raise HTTPException(400,"Not in voting phase")
    from datetime import datetime as dt, timezone
    if e.voting_end and dt.now(timezone.utc).replace(tzinfo=None) > e.voting_end: raise HTTPException(400,"Voting ended")

    if e.vote_type == "approval":
        oids = body.get("candidate_ids") or [body.get("candidate_id")]
        existing = db.query(ElectionVote).filter(
            ElectionVote.election_id == election_id, ElectionVote.voter_id == _u.id).all()
        for ev in existing: db.delete(ev)
        for oid in oids:
            db.add(ElectionVote(election_id=election_id, candidate_id=oid, voter_id=_u.id))
            db.query(ElectionCandidate).filter(ElectionCandidate.id == oid).update(
                {"vote_count": ElectionCandidate.vote_count + 1})
    else:
        oid = body["candidate_id"]
        existing = db.query(ElectionVote).filter(
            ElectionVote.election_id == election_id, ElectionVote.voter_id == _u.id).first()
        if existing:
            db.query(ElectionCandidate).filter(ElectionCandidate.id == existing.candidate_id).update(
                {"vote_count": ElectionCandidate.vote_count - 1})
            existing.candidate_id = oid
        else:
            db.add(ElectionVote(election_id=election_id, candidate_id=oid, voter_id=_u.id))
        db.query(ElectionCandidate).filter(ElectionCandidate.id == oid).update(
            {"vote_count": ElectionCandidate.vote_count + 1})
    db.commit()
    return {"status":"voted"}

# ── Results ──────────────────────────────────────────────────────────────

def calculate_election(election: Election, db: Session):
    candidates = sorted(election.candidates, key=lambda c: c.vote_count, reverse=True)
    total = sum(c.vote_count for c in candidates) or 1

    if election.vote_type == "absolute_majority":
        for c in candidates:
            pct = round(c.vote_count / total * 100, 1)
            elected = pct > 50
            db.merge(ElectionResult(election_id=election.id, candidate_id=c.id,
                      vote_count=c.vote_count, percentage=pct,
                      rank=candidates.index(c)+1, elected=elected))
    elif election.vote_type == "approval":
        total_voters = db.query(ElectionVote.voter_id).filter(
            ElectionVote.election_id == election.id).distinct().count() or 1
        for c in candidates:
            pct = round(c.vote_count / total_voters * 100, 1)
            db.merge(ElectionResult(election_id=election.id, candidate_id=c.id,
                      vote_count=c.vote_count, percentage=pct,
                      rank=candidates.index(c)+1, elected=False))
    else:  # simple_majority
        for c in candidates:
            pct = round(c.vote_count / total * 100, 1)
            db.merge(ElectionResult(election_id=election.id, candidate_id=c.id,
                      vote_count=c.vote_count, percentage=pct,
                      rank=candidates.index(c)+1,
                      elected=(candidates.index(c) == 0)))
    db.commit()

@router.post("/elections/{election_id}/calculate")
def calculate_result(election_id: int, _u: User = Depends(require_permission("election.create")),
                     db: Session = Depends(get_db)):
    e = db.query(Election).filter(Election.id == election_id).first()
    if not e: raise HTTPException(404)
    calculate_election(e, db)
    e.status = "published"; db.commit()
    oplog(db,_u,"election.result","election",str(e.id))
    return _e_dict(e)

@router.get("/elections/{election_id}/results")
def get_results(election_id: int, db: Session = Depends(get_db)):
    results = db.query(ElectionResult).filter(
        ElectionResult.election_id == election_id).order_by(ElectionResult.rank).all()
    return [{"candidate_id":r.candidate_id,"vote_count":r.vote_count,
             "percentage":r.percentage,"rank":r.rank,"elected":r.elected,
             "name":r.candidate.user.username if r.candidate and r.candidate.user else "?"}
            for r in results]
