import sqlite3
import os

db_path = "c:/Users/namem/Desktop/claude_mohit/YantrAI/windows_codes_mohit/3_yantrai_own_codes/2_WIP/22_prome/data/prome.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Migrating database...")

    # Add columns to users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_sharing BOOLEAN DEFAULT 1")
        print("Added is_sharing to users")
    except sqlite3.OperationalError:
        print("is_sharing already exists in users")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN handshake_at DATETIME")
        print("Added handshake_at to users")
    except sqlite3.OperationalError:
        print("handshake_at already exists in users")

    # Create organization_invites table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_invites (
                id TEXT PRIMARY KEY,
                org_id TEXT,
                invitee_id TEXT,
                inviter_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES organizations (id),
                FOREIGN KEY (invitee_id) REFERENCES users (id),
                FOREIGN KEY (inviter_id) REFERENCES users (id)
            )
        """)
        print("Created organization_invites table")
    except Exception as e:
        print(f"Error creating organization_invites table: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
