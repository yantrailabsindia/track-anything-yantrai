from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, index=True)         # "Acme Corp"
    slug = Column(String, unique=True, index=True)          # "acme-corp"
    plan = Column(String, default="free")                   # "free" | "pro" | "enterprise"
    max_users = Column(Integer, default=50)                 # seat limit
    is_active = Column(Boolean, default=True)               # soft disable
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    teams = relationship("Team", back_populates="organization")
    users = relationship("User", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    role = Column(String)  # 'super_admin' | 'admin' | 'team_lead' | 'employee'
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    is_sharing = Column(Boolean, default=True)              # Employee can pause sharing
    handshake_at = Column(DateTime, nullable=True)          # When user joined organization
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    team = relationship("Team", back_populates="members")
    received_invites = relationship("OrganizationInvite", back_populates="invitee", foreign_keys="[OrganizationInvite.invitee_id]")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="teams")
    members = relationship("User", back_populates="team")


class OrganizationInvite(Base):
    __tablename__ = "organization_invites"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"))
    invitee_id = Column(String, ForeignKey("users.id"))
    inviter_id = Column(String, ForeignKey("users.id"))     # Who sent the invite
    status = Column(String, default="pending")              # "pending" | "accepted" | "declined"
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    invitee = relationship("User", foreign_keys=[invitee_id], back_populates="received_invites")
    inviter = relationship("User", foreign_keys=[inviter_id])


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (
        Index("ix_activity_org_timestamp", "org_id", "timestamp"),
        Index("ix_activity_org_timestamp_type", "org_id", "timestamp", "event_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True)
    data = Column(JSON)  # Stores window title, duration, keystrokes, etc.


class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    filename = Column(String)
    screenshot_url = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Chatroom(Base):
    __tablename__ = "chatrooms"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    creator_id = Column(String, ForeignKey("users.id"))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    is_shared = Column(Boolean, default=False)  # Private by default
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User")
    organization = relationship("Organization")
    team = relationship("Team")
    messages = relationship("ChatMessage", back_populates="chatroom")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    chatroom_id = Column(String, ForeignKey("chatrooms.id"), index=True)
    user_id = Column(String, ForeignKey("users.id"))
    role = Column(String)  # "user" or "ai"
    content = Column(String)
    response_data = Column(JSON, nullable=True)  # Full AI response with metrics/charts
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    chatroom = relationship("Chatroom", back_populates="messages")
    user = relationship("User")


# ============================================================================
# CCTV Agent Models
# ============================================================================


class CameraLocation(Base):
    __tablename__ = "camera_locations"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)  # e.g., "Building A Lobby"
    address = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    cameras = relationship("Camera", back_populates="location")


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        Index("ix_camera_org_location", "org_id", "location_id"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    location_id = Column(String, ForeignKey("camera_locations.id"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)  # e.g., "Entrance Cam 1"
    ip_address = Column(String, nullable=False)
    onvif_port = Column(Integer, default=80)
    rtsp_url = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    model = Column(String, nullable=True)
    hardware_id = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)
    snapshot_interval_seconds = Column(Integer, default=300)
    jpeg_quality = Column(Integer, default=85)
    resolution_profile = Column(String, default="sub")  # "main" or "sub"
    frame_rate_fps = Column(Integer, default=10)  # Configurable frame rate (5, 10, 30)
    status = Column(String, default="offline")  # "online", "offline", "error"
    last_seen_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    location = relationship("CameraLocation", back_populates="cameras")
    organization = relationship("Organization")
    snapshots = relationship("CCTVSnapshot", back_populates="camera")


class CCTVSnapshot(Base):
    __tablename__ = "cctv_snapshots"
    __table_args__ = (
        Index("ix_snapshot_org_location_camera_date_hour", "org_id", "location_id", "camera_id", "date_bucket", "hour_bucket"),
        Index("ix_snapshot_org_timestamp", "org_id", "captured_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=False, index=True)
    location_id = Column(String, ForeignKey("camera_locations.id"), nullable=False, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    captured_at = Column(DateTime, nullable=False, index=True)  # When frame was grabbed
    hour_bucket = Column(Integer, nullable=False)  # 0-23
    date_bucket = Column(String, nullable=False)  # "YYYY-MM-DD"
    gcs_path = Column(String, nullable=False)  # Full GCS object path
    gcs_url = Column(String, nullable=True)  # Signed or public URL
    file_size_bytes = Column(Integer, nullable=True)
    resolution = Column(String, nullable=True)  # e.g., "1920x1080"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    camera = relationship("Camera", back_populates="snapshots")
    location = relationship("CameraLocation")
    organization = relationship("Organization")


class CCTVAgentRegistration(Base):
    __tablename__ = "cctv_agent_registrations"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    agent_name = Column(String, nullable=False)  # e.g., "site-building-a"
    api_key = Column(String, unique=True, nullable=False, index=True)
    location_id = Column(String, ForeignKey("camera_locations.id"), nullable=True)
    status = Column(String, default="offline")  # "online", "offline", "error"
    last_heartbeat_at = Column(DateTime, nullable=True)
    config = Column(JSON, nullable=True)  # Agent-reported config snapshot
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    location = relationship("CameraLocation")
