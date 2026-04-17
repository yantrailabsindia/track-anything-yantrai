from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Organization, User, Team
from backend.auth import verify_token
from typing import Optional, List
from datetime import datetime

router = APIRouter()

def get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)

class CreateOrgRequest(BaseModel):
    name: str
    slug: str
    plan: Optional[str] = "free"
    max_users: Optional[int] = 50

class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    max_users: Optional[int] = None
    is_active: Optional[bool] = None

@router.get("/")
def list_organizations(request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data or token_data["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")

    orgs = db.query(Organization).all()
    result = []
    for org in orgs:
        user_count = db.query(User).filter(User.org_id == org.id).count()
        team_count = db.query(Team).filter(Team.org_id == org.id).count()
        result.append({
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "max_users": org.max_users,
            "is_active": org.is_active,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "user_count": user_count,
            "team_count": team_count,
        })
    return result

@router.post("/")
def create_organization(req: CreateOrgRequest, request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data or token_data["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")

    existing = db.query(Organization).filter((Organization.name == req.name) | (Organization.slug == req.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization with this name or slug already exists")

    new_org = Organization(
        name=req.name,
        slug=req.slug,
        plan=req.plan,
        max_users=req.max_users,
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    return {
        "id": new_org.id,
        "name": new_org.name,
        "slug": new_org.slug,
        "plan": new_org.plan,
        "max_users": new_org.max_users,
        "is_active": new_org.is_active,
        "created_at": new_org.created_at.isoformat(),
    }

@router.get("/{org_id}")
def get_org_details(org_id: str, request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)
    
    # Only super admin or org admin can see details
    if token_data["role"] != "super_admin" and token_data["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    user_count = db.query(User).filter(User.org_id == org.id).count()
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan,
        "max_users": org.max_users,
        "is_active": org.is_active,
        "created_at": org.created_at.isoformat(),
        "user_count": user_count
    }

@router.patch("/{org_id}")
def update_organization(org_id: str, req: UpdateOrgRequest, request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data or token_data["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if req.name is not None: org.name = req.name
    if req.plan is not None: org.plan = req.plan
    if req.max_users is not None: org.max_users = req.max_users
    if req.is_active is not None: org.is_active = req.is_active

    db.commit()
    return {"status": "ok", "id": org_id}
