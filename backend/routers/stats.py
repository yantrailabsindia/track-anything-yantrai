from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from backend.services.aggregator import Aggregator
from backend.database import get_db
from backend.auth import verify_token
from datetime import datetime
from typing import Optional

router = APIRouter()

def _get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)

@router.get("/")
def get_stats(request: Request, date: Optional[str] = None, device_id: Optional[str] = None, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    org_id = token_data["org_id"]
    # Employees see only their own data; admins/team_leads see org-wide
    user_id = token_data["id"] if token_data.get("role") == "employee" else None
    return Aggregator.compute_stats(db, date, org_id=org_id, device_id=device_id, user_id=user_id)
