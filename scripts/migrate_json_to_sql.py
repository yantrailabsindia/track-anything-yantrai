"""
One-time migration: move existing JSON data into the SQLite database.

Usage:
    cd 22_prome
    python -m scripts.migrate_json_to_sql
"""

import sys, json
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import engine, SessionLocal
from backend.models import Base, User, Team, ActivityLog
from backend.auth import _hash_password


def migrate():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    data_dir = ROOT / "data"
    migrated = {"users": 0, "teams": 0, "logs": 0}

    # --- Users ---
    users_file = data_dir / "users.json"
    if users_file.exists():
        with open(users_file) as f:
            users = json.load(f)
        for u in users:
            if db.query(User).filter(User.username == u.get("username")).first():
                continue
            user = User(
                id=u.get("id"),
                username=u["username"],
                password_hash=u.get("password_hash", _hash_password("changeme")),
                name=u.get("name", u["username"]),
                role=u.get("role", "employee"),
                team_id=u.get("team_id"),
            )
            db.add(user)
            migrated["users"] += 1
        db.commit()
        print(f"  [OK] Migrated {migrated['users']} users")
    else:
        print("  [--] No users.json found, skipping")

    # --- Teams ---
    teams_file = data_dir / "teams.json"
    if teams_file.exists():
        with open(teams_file) as f:
            teams = json.load(f)
        for t in teams:
            if db.query(Team).filter(Team.name == t["name"]).first():
                continue
            team = Team(
                id=t.get("id"),
                name=t["name"],
                description=t.get("description", ""),
            )
            db.add(team)
            migrated["teams"] += 1
        db.commit()
        print(f"  [OK] Migrated {migrated['teams']} teams")
    else:
        print("  [--] No teams.json found, skipping")

    # --- Activity Logs ---
    logs_dir = data_dir / "logs"
    if logs_dir.exists():
        for log_file in sorted(logs_dir.glob("*.json")):
            with open(log_file) as f:
                try:
                    entries = json.load(f)
                except json.JSONDecodeError:
                    print(f"  [ERR] Could not parse {log_file.name}, skipping")
                    continue
            batch = []
            for entry in entries:
                ts_str = entry.get("timestamp", datetime.now().isoformat())
                try:
                    ts = datetime.fromisoformat(ts_str)
                except (ValueError, TypeError):
                    ts = datetime.now()

                log = ActivityLog(
                    device_id=entry.get("device_id", "unknown"),
                    timestamp=ts,
                    event_type=entry.get("event_type", "unknown"),
                    data=entry.get("data", {}),
                )
                batch.append(log)
            db.add_all(batch)
            db.commit()
            migrated["logs"] += len(batch)
            print(f"  [OK] {log_file.name}: {len(batch)} entries")
        print(f"  [OK] Migrated {migrated['logs']} total log entries")
    else:
        print("  [--] No logs directory found, skipping")

    db.close()
    print(f"\nMigration complete: {migrated}")


if __name__ == "__main__":
    print("ProMe JSON -> SQL Migration\n")
    migrate()
