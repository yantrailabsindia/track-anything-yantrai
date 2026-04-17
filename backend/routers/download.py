from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from backend.auth import verify_token
from pathlib import Path

router = APIRouter()

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "dist"

# ─── Windows Agent (ProMe) ──────────────────────────────────

@router.get("/windows-agent")
def download_windows_agent(request: Request):
    """Download ProMe Windows Agent (Desktop Tracker)."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    token = None
    if auth_header:
        token = auth_header.replace("Bearer ", "")
    else:
        # Check query parameter for direct link support
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    exe_path = DIST_DIR / "ProMe.exe"
    if not exe_path.exists():
        raise HTTPException(status_code=404, detail="Windows Agent build not available yet. Contact admin.")

    response = FileResponse(
        path=str(exe_path),
        filename="ProMe.exe",
        media_type="application/octet-stream"
    )
    # Disable caching to ensure latest version is downloaded
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ─── CCTV Agent ────────────────────────────────────────────

@router.get("/cctv-agent")
def download_cctv_agent(request: Request):
    """Download CCTV Agent (Snapshot Capture Service)."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    token = None
    if auth_header:
        token = auth_header.replace("Bearer ", "")
    else:
        # Check query parameter for direct link support
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    exe_path = DIST_DIR / "CCTVAgent.exe"
    if not exe_path.exists():
        raise HTTPException(status_code=404, detail="CCTV Agent build not available yet. Contact admin.")

    response = FileResponse(
        path=str(exe_path),
        filename="CCTVAgent.exe",
        media_type="application/octet-stream"
    )
    # Disable caching to ensure latest version is downloaded
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ─── Availability Checks ───────────────────────────────────

@router.get("/check")
def check_download_available():
    """Check if agents are available (no auth required)."""
    windows_agent_path = DIST_DIR / "ProMe.exe"
    cctv_agent_path = DIST_DIR / "CCTVAgent.exe"
    return {
        "windows_agent": windows_agent_path.exists(),
        "cctv_agent": cctv_agent_path.exists(),
    }

# ─── Backward Compatibility ────────────────────────────────

@router.get("/")
def download_agent(request: Request):
    """Backward compatibility: Download Windows Agent (ProMe)."""
    return download_windows_agent(request)
