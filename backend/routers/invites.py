from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import OrganizationInvite, User, Organization
from backend.auth import verify_token
from typing import List, Optional
from datetime import datetime

router = APIRouter()

def get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)

class SendInviteRequest(BaseModel):
    username: str  # Invite by username

class InviteResponse(BaseModel):
    id: str
    org_id: str
    org_name: str
    inviter_name: str
    status: str
    created_at: str

@router.post("/send")
def send_invite(req: SendInviteRequest, request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data or token_data["role"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin permissions required to send invites")

    org_id = token_data["org_id"]
    if not org_id:
         raise HTTPException(status_code=400, detail="Inviter must be part of an organization")

    # Find the target user
    invitee = db.query(User).filter(User.username == req.username).first()
    if not invitee:
        raise HTTPException(status_code=404, detail=f"User '{req.username}' not found")

    if invitee.org_id:
        raise HTTPException(status_code=400, detail="User is already part of an organization")

    # Check for existing pending invite
    existing = db.query(OrganizationInvite).filter(
        OrganizationInvite.org_id == org_id,
        OrganizationInvite.invitee_id == invitee.id,
        OrganizationInvite.status == "pending"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Invitation already sent")

    new_invite = OrganizationInvite(
        org_id=org_id,
        invitee_id=invitee.id,
        inviter_id=token_data["id"]
    )
    db.add(new_invite)
    db.commit()
    
    return {"status": "ok", "message": f"Invite sent to {req.username}"}

@router.get("/my", response_model=List[InviteResponse])
def get_my_invites(request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)

    invites = db.query(OrganizationInvite).filter(
        OrganizationInvite.invitee_id == token_data["id"],
        OrganizationInvite.status == "pending"
    ).all()

    result = []
    for inv in invites:
        org = db.query(Organization).filter(Organization.id == inv.org_id).first()
        inviter = db.query(User).filter(User.id == inv.inviter_id).first()
        result.append({
            "id": inv.id,
            "org_id": inv.org_id,
            "org_name": org.name if org else "Unknown Organization",
            "inviter_name": inviter.name if inviter else "Unknown User",
            "status": inv.status,
            "created_at": inv.created_at.isoformat()
        })
    return result

@router.post("/{invite_id}/accept")
def accept_invite(invite_id: str, request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)

    invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.id == invite_id,
        OrganizationInvite.invitee_id == token_data["id"],
        OrganizationInvite.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found or already processed")

    # Complete the Handshake
    user = db.query(User).filter(User.id == token_data["id"]).first()
    user.org_id = invite.org_id
    user.handshake_at = datetime.utcnow()
    
    invite.status = "accepted"
    
    db.commit()
    return {"status": "ok", "message": f"Successfully joined the organization"}

@router.post("/{invite_id}/decline")
def decline_invite(invite_id: str, request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)

    invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.id == invite_id,
        OrganizationInvite.invitee_id == token_data["id"],
        OrganizationInvite.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invite.status = "declined"
    db.commit()
    return {"status": "ok", "message": "Invitation declined"}
