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
def get_activity(request: Request, date: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, device_id: Optional[str] = None, limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    token_data = _get_token_data(request)
    if not token_data:
        raise HTTPException(status_code=401)

    # Filter by org_id from token; employees see only their own data
    org_id = token_data["org_id"]
    user_id = token_data["id"] if token_data.get("role") == "employee" else None

    # Date range query takes priority over single date
    if start_date and end_date:
        limit = min(limit, 5000)  # higher cap for multi-day range
        return Aggregator.get_logs_for_range(db, start_date, end_date, org_id=org_id, device_id=device_id, user_id=user_id, limit=limit, offset=offset)

    # Clamp limit for single-day queries
    limit = min(limit, 500)

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    return Aggregator.get_logs_for_date(db, date, org_id=org_id, device_id=device_id, user_id=user_id, limit=limit, offset=offset)
