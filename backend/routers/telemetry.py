"""
Telemetry ingest endpoint — receives data from the ProMe desktop agent.
Now persists to SQL via SQLAlchemy instead of JSON files.
Org-scoped: Every log and screenshot is stamped with the organization ID.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request, Body
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import shutil

from backend.database import get_db
from backend.models import ActivityLog, Screenshot, User
from backend.auth import verify_token_lenient

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _get_token_data(request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        # Fallback to checking payload if not in header (for some agents)
        return None
    token = auth_header.replace("Bearer ", "")
    return verify_token_lenient(token)


@router.post("/logs")
async def ingest_logs(request: Request, payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Receive a batch of log entries from the desktop agent.
    Expected: { "device_id": "...", "entries": [ {...}, ... ] }
    """
    token_data = _get_token_data(request)
    if not token_data:
        # For now, we allow unauthenticated if we can't find a token, 
        # but in a real app this would be required.
        # We'll try to find a user by device_id if possible in the future.
        user_id = None
        org_id = None
    else:
        user_id = token_data["id"]
        org_id = token_data["org_id"]

    entries = payload.get("entries", [])
    device_id = payload.get("device_id", "unknown")

    if not entries:
        raise HTTPException(status_code=400, detail="No entries provided")

    try:
        db_logs = []
        for entry in entries:
            ts_str = entry.get("timestamp", datetime.now().isoformat())
            try:
                ts = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                ts = datetime.now()

            log = ActivityLog(
                device_id=device_id,
                user_id=user_id,
                org_id=org_id,
                timestamp=ts,
                event_type=entry.get("event_type", "unknown"),
                data=entry.get("data", {}),
            )
            db_logs.append(log)

        db.add_all(db_logs)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving logs: {e}")

    return {"status": "ok", "received": len(entries)}


@router.post("/screenshot")
async def ingest_screenshot(
    request: Request,
    file: UploadFile = File(...),
    device_id: str = Form("unknown"),
    captured_at: str = Form(None),
    db: Session = Depends(get_db),
):
    """
    Receive a screenshot from the desktop agent.
    Saves the file to disk and records metadata in the DB.
    Uses the capture time from the agent (when the screenshot was actually taken),
    not the server receive time.
    """
    token_data = _get_token_data(request)
    user_id = token_data["id"] if token_data else None
    org_id = token_data["org_id"] if token_data else None

    # Use the capture time from the agent if provided, otherwise fall back to now
    if captured_at:
        try:
            timestamp = datetime.fromisoformat(captured_at)
        except (ValueError, TypeError):
            timestamp = datetime.now()
    else:
        timestamp = datetime.now()

    # Use the original uploaded filename to avoid creating duplicates
    # in the shared screenshots directory
    filename = file.filename or f"{device_id}_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.png"
    filepath = SCREENSHOTS_DIR / filename

    # Only save if file doesn't already exist (desktop and backend share the directory)
    if not filepath.exists():
        try:
            with open(filepath, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving screenshot: {e}")

    # Record metadata in DB
    screenshot_record = Screenshot(
        device_id=device_id,
        user_id=user_id,
        org_id=org_id,
        filename=filename,
        screenshot_url=f"/screenshots/{filename}",
        timestamp=timestamp,
    )
    db.add(screenshot_record)
    db.commit()

    return {"status": "ok", "filename": filename}


@router.post("/heartbeat")
async def heartbeat(payload: dict):
    """
    Simple heartbeat so the agent can confirm the server is reachable.
    """
    return {
        "status": "ok",
        "server_time": datetime.now().isoformat(),
        "device_id": payload.get("device_id", "unknown"),
    }
