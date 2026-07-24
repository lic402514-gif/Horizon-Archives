"""RBAC API — roles & permissions."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Role, Permission, user_roles, role_permissions
from app.auth import require_permission

router = APIRouter(prefix="/api", tags=["rbac"])


@router.get("/roles")
def list_roles(_u: User = Depends(require_permission("role.read")), db: Session = Depends(get_db)):
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "description": r.description,
             "permissions": [p.code for p in r.permissions]} for r in roles]


@router.post("/roles", status_code=201)
def create_role(body: dict, _u: User = Depends(require_permission("role.create")),
                db: Session = Depends(get_db)):
    r = Role(name=body["name"], description=body.get("description", ""))
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "name": r.name, "description": r.description}


@router.delete("/roles/{role_id}")
def delete_role(role_id: int, _u: User = Depends(require_permission("role.delete")),
                db: Session = Depends(get_db)):
    db.execute(user_roles.delete().where(user_roles.c.role_id == role_id))
    db.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))
    r = db.query(Role).filter(Role.id == role_id).first()
    if r: db.delete(r)
    db.commit()
    return {"deleted": True}


@router.get("/permissions")
def list_permissions(_u: User = Depends(require_permission("role.read")), db: Session = Depends(get_db)):
    return [{"id": p.id, "code": p.code, "description": p.description} for p in db.query(Permission).all()]


@router.put("/roles/{role_id}/permissions")
def update_role_permissions(role_id: int, body: list[str],
                            _u: User = Depends(require_permission("permission.assign")),
                            db: Session = Depends(get_db)):
    r = db.query(Role).filter(Role.id == role_id).first()
    if not r: raise HTTPException(404)
    db.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))
    for code in body:
        p = db.query(Permission).filter(Permission.code == code).first()
        if p:
            db.execute(role_permissions.insert().values(role_id=role_id, permission_id=p.id))
    db.commit()
    return {"status": "updated"}


@router.get("/users/{user_id}/roles")
def get_user_roles(user_id: int, _u: User = Depends(require_permission("role.read")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404)
    return [{"id": r.id, "name": r.name} for r in user.roles]


@router.put("/users/{user_id}/roles/{role_id}")
def assign_user_role(user_id: int, role_id: int,
                     _u: User = Depends(require_permission("user.assign_role")),
                     db: Session = Depends(get_db)):
    exists = db.execute(user_roles.select().where(
        user_roles.c.user_id == user_id, user_roles.c.role_id == role_id
    )).first()
    if not exists:
        db.execute(user_roles.insert().values(user_id=user_id, role_id=role_id))
        db.commit()
    return {"status": "assigned"}


@router.delete("/users/{user_id}/roles/{role_id}")
def remove_user_role(user_id: int, role_id: int,
                     _u: User = Depends(require_permission("user.assign_role")),
                     db: Session = Depends(get_db)):
    db.execute(user_roles.delete().where(
        user_roles.c.user_id == user_id, user_roles.c.role_id == role_id
    ))
    db.commit()
    return {"status": "removed"}
