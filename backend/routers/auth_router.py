from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.auth import authenticate, create_token, verify_token, create_user, list_users, get_user_by_id
from backend.database import get_db
from typing import Optional

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    name: str
    role: str = "employee"
    team_id: Optional[str] = None
    org_id: Optional[str] = None

def get_token_data(request: Request):
    """Extract and verify token from Authorization header."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)

class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user)
    return {"token": token, "user": user}

@router.post("/verify-password")
def verify_password(req: LoginRequest, db: Session = Depends(get_db)):
    """Verify password without creating a token. Used for logout confirmation."""
    user = authenticate(db, req.username, req.password)
    return {"valid": user is not None}

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        # Create user with No Org ID (Personal Mode)
        user = create_user(db, req.username, req.password, req.name, role="employee", org_id=None)
        token = create_token(user)
        return {"token": token, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me")
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = get_user_by_id(db, token_data["id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/users")
def create_new_user(req: CreateUserRequest, request: Request, db: Session = Depends(get_db)):
    token_data = get_token_data(request)
    if not token_data or token_data["role"] not in ["super_admin", "admin", "team_lead"]:
        raise HTTPException(status_code=403, detail="Sufficient permissions required")
    
    target_org_id = req.org_id
    
    # Non-super_admins can only create users within their own organization
    if token_data["role"] != "super_admin":
        if target_org_id and target_org_id != token_data["org_id"]:
            raise HTTPException(status_code=403, detail="Cannot create users for other organizations")
        target_org_id = token_data["org_id"]
    
    # Team Leads can only create users for THEIR team
    if token_data["role"] == "team_lead":
        current_user = get_user_by_id(db, token_data["id"])
        if not current_user or current_user.get("team_id") != req.team_id:
             raise HTTPException(status_code=403, detail="Team Leads can only create users for their own team")

    try:
        user = create_user(db, req.username, req.password, req.name, req.role, req.team_id, target_org_id)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users")
def get_all_users(request: Request, db: Session = Depends(get_db), team: Optional[str] = None, org: Optional[str] = None):
    token_data = get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)
    
    if token_data["role"] == "super_admin":
        # Super admins can see all users or filter by org
        return list_users(db, team_filter=team, org_filter=org)
    elif token_data["role"] == "admin":
        # Admins only see their org
        return list_users(db, team_filter=team, org_filter=token_data["org_id"])
    elif token_data["role"] == "team_lead":
        current_user = get_user_by_id(db, token_data["id"])
        if not current_user:
             raise HTTPException(status_code=401)
        # Team leads only see their team within their org
        return list_users(db, team_filter=current_user.get("team_id"), org_filter=token_data["org_id"])
    else:
        raise HTTPException(status_code=403, detail="Access denied")
