#!/usr/bin/env python
"""
Migration runner — applies SQL migrations to the database.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from backend.database import engine, SessionLocal

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def run_migrations():
    """Apply all SQL migration files in order."""
    if not MIGRATIONS_DIR.exists():
        print(f"Migrations directory not found: {MIGRATIONS_DIR}")
        return

    # Get all .sql files sorted by name
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migration_files:
        print("No migration files found")
        return

    db = SessionLocal()
    try:
        for migration_file in migration_files:
            print(f"Applying migration: {migration_file.name}...")

            with open(migration_file, "r") as f:
                sql = f.read()

            # Execute the SQL
            with engine.connect() as conn:
                # Split by semicolon and execute each statement
                statements = [s.strip() for s in sql.split(";") if s.strip()]
                for statement in statements:
                    conn.execute(text(statement))
                    conn.commit()

            print(f"  [OK] {migration_file.name} completed")

        print("\nAll migrations applied successfully!")
    except Exception as e:
        print(f"Migration error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migrations()
