import hashlib
import json
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import User, Organization
from backend.database import SessionLocal

import os
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SECRET_KEY = os.getenv("SECRET_KEY", "prome-secret-key-change-in-production-2026")
TOKEN_EXPIRY_HOURS = 24

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_default_users():
    """Create default organization and super_admin account if none exist."""
    db = SessionLocal()
    try:
        # Ensure a default organization exists
        default_org = db.query(Organization).filter(Organization.slug == "default").first()
        if not default_org:
            default_org = Organization(
                name="Default Organization",
                slug="default",
                plan="enterprise",
                max_users=999,
                is_active=True,
            )
            db.add(default_org)
            db.commit()
            db.refresh(default_org)
            print(f"Default organization created (id={default_org.id})")

        # Ensure a super_admin account exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin",
                password_hash=_hash_password("admin"),
                name="Super Administrator",
                role="super_admin",
                org_id=default_org.id,
            )
            db.add(admin_user)
            db.commit()
            print("Default super_admin account created in DB (admin/admin)")
        elif admin.role != "super_admin":
            # Upgrade existing admin to super_admin
            admin.role = "super_admin"
            if not admin.org_id:
                admin.org_id = default_org.id
            db.commit()
            print("Existing admin upgraded to super_admin")
    finally:
        db.close()

def authenticate(db: Session, username: str, password: str) -> dict | None:
    pw_hash = _hash_password(password)
    user = db.query(User).filter(User.username == username, User.password_hash == pw_hash).first()
    if user:
        # Fetch org name if user has an org
        org_name = None
        if user.org_id:
            org = db.query(Organization).filter(Organization.id == user.org_id).first()
            if org:
                org_name = org.name
        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role,
            "org_id": user.org_id,
            "org_name": org_name,
            "team_id": user.team_id,
            "created_at": user.created_at.isoformat()
        }
    return None

def create_token(user: dict) -> str:
    """Simple token: base64(user_id|role|org_id|expiry|signature)"""
    import base64, hmac
    org_id = user.get('org_id') or ''
    expiry = (datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)).isoformat()
    payload = f"{user['id']}|{user['role']}|{org_id}|{expiry}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    token = base64.b64encode(f"{payload}|{signature}".encode()).decode()
    return token

def verify_token(token: str) -> dict | None:
    """Verify token and return user info including org_id."""
    import base64, hmac
    try:
        decoded = base64.b64decode(token).decode()
        parts = decoded.split("|")
        if len(parts) != 5:
            return None
        user_id, role, org_id, expiry, signature = parts

        # Check expiry
        if datetime.fromisoformat(expiry) < datetime.now():
            return None

        # Verify signature
        payload = f"{user_id}|{role}|{org_id}|{expiry}"
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if signature != expected_sig:
            return None

        return {"id": user_id, "role": role, "org_id": org_id or None}
    except Exception:
        return None

def verify_token_lenient(token: str) -> dict | None:
    """Verify token signature but skip expiry check.
    Used by telemetry ingestion so the desktop agent's logs are always
    stamped with the correct user_id/org_id even after token expiry."""
    import base64, hmac
    try:
        decoded = base64.b64decode(token).decode()
        parts = decoded.split("|")
        if len(parts) != 5:
            return None
        user_id, role, org_id, expiry, signature = parts

        # Verify signature (skip expiry check)
        payload = f"{user_id}|{role}|{org_id}|{expiry}"
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if signature != expected_sig:
            return None

        return {"id": user_id, "role": role, "org_id": org_id or None}
    except Exception:
        return None

def get_user_by_id(db: Session, user_id: str) -> dict | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        org_name = None
        if user.org_id:
            org = db.query(Organization).filter(Organization.id == user.org_id).first()
            if org:
                org_name = org.name
        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role,
            "org_id": user.org_id,
            "org_name": org_name,
            "team_id": user.team_id,
            "created_at": user.created_at.isoformat()
        }
    return None

def create_user(db: Session, username: str, password: str, name: str,
                role: str = "employee", team_id: str = None, org_id: str = None) -> dict:
    if db.query(User).filter(User.username == username).first():
        raise ValueError(f"Username '{username}' already exists")
    
    # Validate org seat limit
    if org_id:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org:
            current_count = db.query(User).filter(User.org_id == org_id).count()
            if current_count >= org.max_users:
                raise ValueError(f"Organization '{org.name}' has reached its seat limit ({org.max_users})")

    new_user = User(
        username=username,
        password_hash=_hash_password(password),
        name=name,
        role=role,
        team_id=team_id,
        org_id=org_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "name": new_user.name,
        "role": new_user.role,
        "org_id": new_user.org_id,
        "team_id": new_user.team_id,
        "created_at": new_user.created_at.isoformat()
    }

def list_users(db: Session, role_filter: str = None, team_filter: str = None,
               org_filter: str = None) -> list:
    query = db.query(User)
    if role_filter:
        query = query.filter(User.role == role_filter)
    if team_filter:
        query = query.filter(User.team_id == team_filter)
    if org_filter:
        query = query.filter(User.org_id == org_filter)
    
    users = query.all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "role": u.role,
            "org_id": u.org_id,
            "team_id": u.team_id,
            "created_at": u.created_at.isoformat()
        }
        for u in users
    ]
