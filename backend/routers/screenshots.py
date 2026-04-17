from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Screenshot
from backend.auth import verify_token
from typing import Optional

router = APIRouter()

def _get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token(token)

@router.get("/")
def list_screenshots(request: Request, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)

    org_id = token_data["org_id"]
    user_id = token_data["id"] if token_data.get("role") == "employee" else None

    query = db.query(Screenshot)
    if org_id:
        query = query.filter(Screenshot.org_id == org_id)
    if user_id:
        query = query.filter(Screenshot.user_id == user_id)

    screenshots = query.order_by(Screenshot.timestamp.desc()).limit(50).all()

    return [{"filename": s.filename, "url": s.screenshot_url, "timestamp": s.timestamp.isoformat()} for s in screenshots]
