from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import base64
from pathlib import Path
import os
import logging

from backend.database import get_db
from backend.models import (
    CameraLocation, Camera, CCTVSnapshot, CCTVAgentRegistration,
    Organization
)

router = APIRouter()

# ============================================================================
# Models/Schemas
# ============================================================================

class CameraLocationCreate(BaseModel):
    name: str
    address: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    timezone: Optional[str] = "UTC"


class CameraLocationResponse(BaseModel):
    id: str
    org_id: str
    name: str
    address: Optional[str]
    latitude: Optional[str]
    longitude: Optional[str]
    timezone: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CameraCreate(BaseModel):
    location_id: str
    name: str
    ip_address: str
    onvif_port: int = 80
    rtsp_url: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    snapshot_interval_seconds: int = 300
    jpeg_quality: int = 85
    resolution_profile: str = "sub"


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    snapshot_interval_seconds: Optional[int] = None
    jpeg_quality: Optional[int] = None
    resolution_profile: Optional[str] = None
    is_active: Optional[bool] = None


class CameraResponse(BaseModel):
    id: str
    location_id: str
    org_id: str
    name: str
    ip_address: str
    onvif_port: int
    rtsp_url: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    snapshot_interval_seconds: int
    jpeg_quality: int
    resolution_profile: str
    status: str
    last_seen_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CCTVSnapshotIngest(BaseModel):
    camera_id: str
    captured_at: datetime
    username: str
    image_data: str  # base64-encoded JPEG image
    gcs_path: Optional[str] = None  # Optional for backward compatibility
    file_size_bytes: Optional[int] = None
    resolution: Optional[str] = None


class CCTVSnapshotResponse(BaseModel):
    id: int
    camera_id: str
    location_id: str
    org_id: str
    captured_at: datetime
    hour_bucket: int
    date_bucket: str
    gcs_path: str
    gcs_url: Optional[str]
    file_size_bytes: Optional[int]
    resolution: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AgentHeartbeat(BaseModel):
    agent_id: str
    camera_statuses: dict  # {camera_id: {"status": "online|offline|error", "last_frame": timestamp, ...}}
    system_metrics: Optional[dict] = None  # {cpu: X, memory: Y, disk: Z}


class AgentRegisterRequest(BaseModel):
    org_id: str
    agent_name: str
    location_id: Optional[str] = None


class AgentRegisterResponse(BaseModel):
    agent_id: str
    api_key: str


# ============================================================================
# Middleware: Agent Auth
# ============================================================================

def get_agent_org(api_key: str, db: Session) -> tuple[str, str]:
    """
    Verify agent API key and return (agent_id, org_id).
    Raises HTTPException if invalid.
    """
    agent = db.query(CCTVAgentRegistration).filter(
        CCTVAgentRegistration.api_key == api_key
    ).first()

    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent API key")

    return agent.id, agent.org_id


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/agent/register")
def register_agent(req: AgentRegisterRequest, db: Session = Depends(get_db)):
    """Register a new CCTV agent. Returns API key."""
    # Verify org exists
    org = db.query(Organization).filter(Organization.id == req.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Generate unique API key
    api_key = f"cctv_{secrets.token_urlsafe(32)}"

    agent = CCTVAgentRegistration(
        org_id=req.org_id,
        agent_name=req.agent_name,
        api_key=api_key,
        location_id=req.location_id,
        status="offline"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    return AgentRegisterResponse(
        agent_id=agent.id,
        api_key=api_key
    )


@router.post("/agent/heartbeat")
def agent_heartbeat(req: AgentHeartbeat, api_key: str = Query(...), db: Session = Depends(get_db)):
    """Agent reports status. Updates camera statuses and agent last_heartbeat_at."""
    agent_id, org_id = get_agent_org(api_key, db)

    agent = db.query(CCTVAgentRegistration).filter(
        CCTVAgentRegistration.id == agent_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update agent heartbeat
    agent.last_heartbeat_at = datetime.utcnow()
    agent.status = "online"
    agent.config = {"camera_statuses": req.camera_statuses, "system_metrics": req.system_metrics}

    # Update camera statuses
    for camera_id, status_data in req.camera_statuses.items():
        camera = db.query(Camera).filter(
            Camera.id == camera_id,
            Camera.org_id == org_id
        ).first()
        if camera:
            camera.status = status_data.get("status", "offline")
            camera.last_seen_at = datetime.utcnow()

    db.commit()
    return {"status": "ok"}


@router.post("/locations")
def create_location(req: CameraLocationCreate, org_id: str = Query(...), db: Session = Depends(get_db)):
    """Create a camera location."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    location = CameraLocation(
        org_id=org_id,
        name=req.name,
        address=req.address,
        latitude=req.latitude,
        longitude=req.longitude,
        timezone=req.timezone
    )
    db.add(location)
    db.commit()
    db.refresh(location)

    return CameraLocationResponse.from_orm(location)


@router.get("/locations")
def list_locations(org_id: str = Query(...), db: Session = Depends(get_db)) -> List[CameraLocationResponse]:
    """List all locations for an organization."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    locations = db.query(CameraLocation).filter(
        CameraLocation.org_id == org_id
    ).all()

    return [CameraLocationResponse.from_orm(loc) for loc in locations]


@router.post("/cameras")
def create_camera(req: CameraCreate, org_id: str = Query(...), api_key: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Register a camera. Can be called by admin (with org_id) or agent (with api_key)."""
    # Verify org
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Verify location
    location = db.query(CameraLocation).filter(
        CameraLocation.id == req.location_id,
        CameraLocation.org_id == org_id
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    camera = Camera(
        location_id=req.location_id,
        org_id=org_id,
        name=req.name,
        ip_address=req.ip_address,
        onvif_port=req.onvif_port,
        rtsp_url=req.rtsp_url,
        manufacturer=req.manufacturer,
        model=req.model,
        snapshot_interval_seconds=req.snapshot_interval_seconds,
        jpeg_quality=req.jpeg_quality,
        resolution_profile=req.resolution_profile,
        status="offline"
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)

    return CameraResponse.from_orm(camera)


@router.get("/cameras")
def list_cameras(
    org_id: str = Query(...),
    location_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> List[CameraResponse]:
    """List cameras. Filter by location_id if provided."""
    query = db.query(Camera).filter(Camera.org_id == org_id)

    if location_id:
        query = query.filter(Camera.location_id == location_id)

    cameras = query.all()
    return [CameraResponse.from_orm(cam) for cam in cameras]


@router.patch("/cameras/{camera_id}")
def update_camera(camera_id: str, req: CameraUpdate, org_id: str = Query(...), db: Session = Depends(get_db)):
    """Update camera settings."""
    camera = db.query(Camera).filter(
        Camera.id == camera_id,
        Camera.org_id == org_id
    ).first()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    if req.name is not None:
        camera.name = req.name
    if req.snapshot_interval_seconds is not None:
        camera.snapshot_interval_seconds = req.snapshot_interval_seconds
    if req.jpeg_quality is not None:
        camera.jpeg_quality = req.jpeg_quality
    if req.resolution_profile is not None:
        camera.resolution_profile = req.resolution_profile
    if req.is_active is not None:
        camera.is_active = req.is_active

    db.commit()
    db.refresh(camera)

    return CameraResponse.from_orm(camera)


@router.post("/snapshots")
def ingest_snapshot(req: CCTVSnapshotIngest, api_key: str = Query(...), db: Session = Depends(get_db)):
    """Ingest snapshot from agent with local file storage."""
    agent_id, org_id = get_agent_org(api_key, db)

    # Verify camera
    camera = db.query(Camera).filter(
        Camera.id == req.camera_id,
        Camera.org_id == org_id
    ).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Save image locally
    local_path = None
    try:
        if req.image_data:
            # Decode base64 image
            image_bytes = base64.b64decode(req.image_data)

            # Create folder structure: data/cctv/{username}/{YYYYMMDD}/
            date_str = req.captured_at.strftime("%Y%m%d")
            cctv_dir = Path("data/cctv") / req.username / date_str
            cctv_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename: {CAMERA_ID}_{YYYYMMDD}_{HHMMSS}_{mmm}.jpg
            timestamp_str = req.captured_at.strftime("%Y%m%d_%H%M%S")
            milliseconds = req.captured_at.microsecond // 1000
            filename = f"{req.camera_id}_{timestamp_str}_{milliseconds:03d}.jpg"

            # Save file
            filepath = cctv_dir / filename
            with open(filepath, 'wb') as f:
                f.write(image_bytes)

            local_path = str(filepath)
            file_size = len(image_bytes)
            logging.info(f"Saved CCTV snapshot: {local_path}")

    except Exception as e:
        logging.error(f"Failed to save CCTV snapshot locally: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save snapshot: {str(e)}")

    # Extract hour and date from captured_at
    hour_bucket = req.captured_at.hour
    date_bucket = req.captured_at.strftime("%Y-%m-%d")

    # Use local path if available, fallback to GCS path
    stored_path = local_path or req.gcs_path or ""

    snapshot = CCTVSnapshot(
        camera_id=req.camera_id,
        location_id=camera.location_id,
        org_id=org_id,
        captured_at=req.captured_at,
        hour_bucket=hour_bucket,
        date_bucket=date_bucket,
        gcs_path=stored_path,  # Now stores local path
        file_size_bytes=req.file_size_bytes or len(image_bytes) if req.image_data else None,
        resolution=req.resolution
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return CCTVSnapshotResponse.from_orm(snapshot)


@router.get("/snapshots")
def query_snapshots(
    org_id: str = Query(...),
    location_id: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),  # "YYYY-MM-DD"
    hour: Optional[int] = Query(None),  # 0-23
    skip: int = Query(0),
    limit: int = Query(50),
    db: Session = Depends(get_db)
) -> dict:
    """Query snapshots with filters. Returns paginated results."""
    query = db.query(CCTVSnapshot).filter(CCTVSnapshot.org_id == org_id)

    if location_id:
        query = query.filter(CCTVSnapshot.location_id == location_id)
    if camera_id:
        query = query.filter(CCTVSnapshot.camera_id == camera_id)
    if date:
        query = query.filter(CCTVSnapshot.date_bucket == date)
    if hour is not None:
        query = query.filter(CCTVSnapshot.hour_bucket == hour)

    total = query.count()
    snapshots = query.order_by(CCTVSnapshot.captured_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "snapshots": [CCTVSnapshotResponse.from_orm(s) for s in snapshots]
    }


@router.get("/snapshots/{snapshot_id}/url")
def get_snapshot_url(snapshot_id: int, org_id: str = Query(...), db: Session = Depends(get_db)):
    """Generate signed GCS URL for viewing snapshot."""
    snapshot = db.query(CCTVSnapshot).filter(
        CCTVSnapshot.id == snapshot_id,
        CCTVSnapshot.org_id == org_id
    ).first()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    # In a real implementation, call gcs_service.generate_signed_download_url()
    # For now, return a placeholder
    return {
        "snapshot_id": snapshot_id,
        "gcs_path": snapshot.gcs_path,
        "signed_url": f"https://storage.googleapis.com/[signed_url_placeholder]",
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }


@router.get("/feed/{camera_id}")
def get_latest_cctv_feed(camera_id: str, org_id: str = Query(...), db: Session = Depends(get_db)):
    """Get latest CCTV snapshot for a camera."""
    # Get latest snapshot for this camera
    snapshot = db.query(CCTVSnapshot).filter(
        CCTVSnapshot.camera_id == camera_id,
        CCTVSnapshot.org_id == org_id
    ).order_by(CCTVSnapshot.captured_at.desc()).first()

    if not snapshot:
        raise HTTPException(status_code=404, detail="No snapshots found for this camera")

    # Try to load the image from local disk
    image_data = None
    try:
        if snapshot.gcs_path and Path(snapshot.gcs_path).exists():
            with open(snapshot.gcs_path, 'rb') as f:
                image_bytes = f.read()
                image_data = base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        logging.warning(f"Failed to load image from disk: {e}")

    return {
        "snapshot_id": snapshot.id,
        "camera_id": snapshot.camera_id,
        "captured_at": snapshot.captured_at.isoformat(),
        "image_data": image_data,  # base64-encoded JPEG
        "file_path": snapshot.gcs_path,
        "file_size_bytes": snapshot.file_size_bytes
    }
