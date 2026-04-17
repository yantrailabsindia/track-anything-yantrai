"""
Team management router — create/list teams, assign members.
Fully SQL-backed via SQLAlchemy.
Org-scoped: Admins and team leads only see/manage teams within their own organization.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.auth import verify_token
from backend.database import get_db
from backend.models import Team, User
from typing import Optional
from datetime import datetime

router = APIRouter()


def _get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)


class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class AssignMemberRequest(BaseModel):
    user_id: str


@router.get("/")
def list_teams(request: Request, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    query = db.query(Team)
    
    # Non-super_admins can only see teams for their own organization
    if token_data["role"] != "super_admin":
        query = query.filter(Team.org_id == token_data["org_id"])
    
    teams = query.all()
    result = []
    for team in teams:
        member_count = db.query(User).filter(User.team_id == team.id).count()
        result.append({
            "id": team.id,
            "name": team.name,
            "org_id": team.org_id,
            "description": team.description or "",
            "created_at": team.created_at.isoformat() if team.created_at else None,
            "member_count": member_count,
        })
    return result


@router.post("/")
def create_team(req: CreateTeamRequest, request: Request, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data or token_data["role"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    org_id = token_data["org_id"]
    
    # Check if team with same name exists in this org
    existing = db.query(Team).filter(Team.name.ilike(req.name), Team.org_id == org_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Team '{req.name}' already exists in this organization")

    new_team = Team(
        name=req.name,
        description=req.description or "",
        org_id=org_id,
    )
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    return {
        "id": new_team.id,
        "name": new_team.name,
        "org_id": new_team.org_id,
        "description": new_team.description,
        "created_at": new_team.created_at.isoformat(),
    }


@router.post("/{team_id}/members")
def assign_member(team_id: str, req: AssignMemberRequest, request: Request, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data or token_data["role"] not in ["super_admin", "admin", "team_lead"]:
        raise HTTPException(status_code=403, detail="Sufficient permissions required")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Access check: can only modify teams in same org
    if token_data["role"] != "super_admin" and team.org_id != token_data["org_id"]:
        raise HTTPException(status_code=403, detail="Cannot assign members to teams in other organizations")

    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify user belongs to same org
    if token_data["role"] != "super_admin" and user.org_id != token_data["org_id"]:
        raise HTTPException(status_code=403, detail="User belongs to a different organization")

    user.team_id = team_id
    db.commit()
    return {"status": "ok", "user_id": req.user_id, "team_id": team_id}


@router.delete("/{team_id}/members/{user_id}")
def remove_member(team_id: str, user_id: str, request: Request, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data or token_data["role"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(User).filter(User.id == user_id, User.team_id == team_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in team")
    
    # Access check
    if token_data["role"] != "super_admin" and user.org_id != token_data["org_id"]:
        raise HTTPException(status_code=403, detail="Cannot remove members from teams in other organizations")

    user.team_id = None
    db.commit()
    return {"status": "ok"}


@router.get("/{team_id}/members")
def get_team_members(team_id: str, request: Request, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Access check
    if token_data["role"] != "super_admin" and team.org_id != token_data["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    users = db.query(User).filter(User.team_id == team_id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "role": u.role,
            "org_id": u.org_id,
            "team_id": u.team_id,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
