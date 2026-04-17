"""
Migration script to add Organization support to an existing ProMe SQLite database.
1. Creates the organizations table.
2. Creates a default organization.
3. Adds org_id columns to users, teams, activity_logs, and screenshots.
4. Updates existing records to belong to the default organization.
5. Upgrades the 'admin' user to 'super_admin'.
"""
import sqlite3
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "prome.db"

def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Skipping migration.")
        return

    print(f"Refining database at {DB_PATH}...")
    
    # Backup
    backup_path = DB_PATH.with_suffix(".db.bak")
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created at {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create organizations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            slug TEXT UNIQUE,
            plan TEXT,
            max_users INTEGER,
            is_active BOOLEAN,
            created_at DATETIME
        )
        """)
        print("Table 'organizations' created.")

        # 2. Add default org
        import uuid
        from datetime import datetime
        default_org_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        cursor.execute("SELECT id FROM organizations WHERE slug = 'default'")
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
            INSERT INTO organizations (id, name, slug, plan, max_users, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (default_org_id, "Default Organization", "default", "enterprise", 999, 1, now))
            print(f"Default organization created with ID: {default_org_id}")
        else:
            default_org_id = row[0]
            print(f"Using existing default organization ID: {default_org_id}")

        # 3. Add org_id columns to other tables
        tables_to_update = ["users", "teams", "activity_logs", "screenshots"]
        for table in tables_to_update:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN org_id TEXT REFERENCES organizations(id)")
                print(f"Added 'org_id' column to table: {table}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column 'org_id' already exists in table: {table}")
                else:
                    raise e

        # 4. Update existing records to the default org
        for table in tables_to_update:
            cursor.execute(f"UPDATE {table} SET org_id = ? WHERE org_id IS NULL", (default_org_id,))
            print(f"Updated existing records in '{table}' to belong to default organization.")

        # 5. Upgrade admin to super_admin
        cursor.execute("UPDATE users SET role = 'super_admin' WHERE username = 'admin'")
        print("Admin user upgraded to super_admin.")

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
