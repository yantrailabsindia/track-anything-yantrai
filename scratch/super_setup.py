import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import engine, SessionLocal, Base
from backend.auth import init_default_users, _hash_password, User, Organization
from sqlalchemy import text
import httpx
import json
import time
import secrets

def super_setup():
    # 1. Clear database
    db_path = Path("data/prome.db")
    if db_path.exists():
        db_path.unlink()
        print("Deleted existing database")

    # 2. Create tables via SQLAlchemy
    Base.metadata.create_all(bind=engine)
    print("Core tables created")

    # 3. Initialize default users (creates 'default' org and 'admin' user)
    init_default_users()
    print("Default users initialized")

    # 4. Apply migrations
    migrations_dir = Path("backend/migrations")
    migration_files = sorted(migrations_dir.glob("*.sql"))
    with engine.connect() as conn:
        for migration_file in migration_files:
            print(f"Applying migration: {migration_file.name}")
            with open(migration_file, "r") as f:
                sql = f.read()
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            for statement in statements:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    print(f"  Warning on statement: {e}")
            conn.commit()
    print("Migrations applied")

    # 5. Create 'mohit' user and his organization
    db = SessionLocal()
    try:
        # Create a specific organization for mohit
        org = Organization(
            name="Mohit Org",
            slug="mohit-org",
            plan="pro"
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        print(f"Created organization: {org.name} ({org.id})")

        # Create mohit user
        mohit = User(
            username="mohit",
            password_hash=_hash_password("mohit123"),
            name="Mohit",
            role="admin",
            org_id=org.id
        )
        db.add(mohit)
        db.commit()
        db.refresh(mohit)
        print(f"Created user: {mohit.username} ({mohit.id})")

        org_id = org.id
        user_id = mohit.id
    finally:
        db.close()

    # 6. Start the backend in separate process (manual step or use subprocess)
    # Since I'm in a script, I'll just use direct DB calls for the rest as well
    # OR start backend and use API. I'll use direct DB for speed.
    
    db = SessionLocal()
    try:
        # Register Location
        from backend.models import CameraLocation, Camera, CCTVAgentRegistration
        location = CameraLocation(
            org_id=org_id,
            name="Office",
            timezone="IST"
        )
        db.add(location)
        db.commit()
        db.refresh(location)
        print(f"Created location: {location.name} ({location.id})")

        # Register Camera
        camera = Camera(
            location_id=location.id,
            org_id=org_id,
            name="Front Door",
            ip_address="192.168.1.12",
            rtsp_url="rtsp://admin:mohit123@192.168.1.12:554/live/channel0",
            snapshot_interval_seconds=5,
            frame_rate_fps=1
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)
        print(f"Created camera: {camera.name} ({camera.id})")

        # Register Agent
        api_key = f"cctv_{secrets.token_urlsafe(32)}"
        agent = CCTVAgentRegistration(
            org_id=org_id,
            agent_name="site-01",
            api_key=api_key,
            location_id=location.id,
            status="offline"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        print(f"Created agent: {agent.agent_name} with API Key: {api_key}")

        # 7. Update config.json
        config_path = Path.home() / "CCTVAgent" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # Update API URL
            config["cloud"]["api_url"] = "http://localhost:8765"
            config["cloud"]["api_key"] = api_key
            config["cloud"]["agent_id"] = agent.id
            
            # Update user info (generate a token manually)
            import base64, hmac
            SECRET_KEY = "prome-secret-key-change-in-production-2026"
            expiry = (datetime.now() + timedelta(hours=24)).isoformat()
            payload = f"{user_id}|admin|{org_id}|{expiry}"
            signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
            token = base64.b64encode(f"{payload}|{signature}".encode()).decode()

            config["user"] = {
                "user_id": user_id,
                "username": "mohit",
                "token": token,
                "api_url": "http://localhost:8000",
                "org_id": org_id
            }
            
            # Update devices and streams
            config["devices"] = [{
                "id": camera.id,
                "location_id": location.id,
                "ip": "192.168.1.12",
                "channels": [{
                    "channel_number": 1,
                    "enabled": True,
                    "name": "PROFILE_1",
                    "sub_stream_uri": f"rtsp://admin:mohit123@192.168.1.12:554/live/channel0",
                    "token": "PROFILE_000"
                }],
                "is_active": True,
                "type": "Camera"
            }]
            config["cloud"]["active_streams"] = [{
                "id": camera.id,
                "name": "Front Door",
                "ip": "192.168.1.12",
                "port": 554,
                "rtsp_url": f"rtsp://admin:mohit123@192.168.1.12:554/live/channel0",
                "active": True,
                "snapshot_interval_seconds": 5,
                "fps_setting": 1
            }]
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            print(f"Updated config.json at {config_path}")

    finally:
        db.close()

if __name__ == "__main__":
    import hashlib
    from datetime import datetime, timedelta
    super_setup()
