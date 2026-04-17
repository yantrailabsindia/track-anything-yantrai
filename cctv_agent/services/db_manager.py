"""
Local SQLite database manager for CCTV agent.
Tracks queue status, snapshots, and logs.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class DBManager:
    """
    Manages local SQLite database for queue and status tracking.
    """

    def __init__(self, db_path: Path):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Snapshot queue table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS snapshot_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        camera_id TEXT NOT NULL,
                        location_id TEXT NOT NULL,
                        org_id TEXT NOT NULL,
                        captured_at TEXT NOT NULL,
                        local_file_path TEXT NOT NULL,
                        gcs_path TEXT,
                        file_size_bytes INTEGER,
                        resolution TEXT,
                        status TEXT DEFAULT 'pending',
                        retry_count INTEGER DEFAULT 0,
                        last_error TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        uploaded_at TEXT
                    )
                """)

                # Agent status table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS agent_status (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_queue_status
                    ON snapshot_queue(status)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_queue_camera
                    ON snapshot_queue(camera_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_queue_created
                    ON snapshot_queue(created_at)
                """)

                conn.commit()
                logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def add_snapshot_to_queue(
        self,
        camera_id: str,
        location_id: str,
        org_id: str,
        captured_at: datetime,
        local_file_path: str,
        gcs_path: str,
        file_size_bytes: int,
        resolution: Optional[str] = None
    ) -> bool:
        """Add snapshot to upload queue."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO snapshot_queue
                    (camera_id, location_id, org_id, captured_at, local_file_path, gcs_path, file_size_bytes, resolution)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    camera_id, location_id, org_id,
                    captured_at.isoformat(),
                    local_file_path, gcs_path, file_size_bytes, resolution
                ))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to add snapshot to queue: {e}")
            return False

    def get_pending_snapshots(self, limit: int = 100) -> List[Dict]:
        """Get pending snapshots from queue."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM snapshot_queue
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get pending snapshots: {e}")
            return []

    def mark_uploaded(self, snapshot_id: int) -> bool:
        """Mark snapshot as uploaded."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE snapshot_queue
                    SET status = 'uploaded', uploaded_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (snapshot_id,))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to mark snapshot as uploaded: {e}")
            return False

    def mark_failed(self, snapshot_id: int, error: str, retry_count: int) -> bool:
        """Mark snapshot as failed and increment retry count."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE snapshot_queue
                    SET status = 'failed', last_error = ?, retry_count = ?
                    WHERE id = ?
                """, (error, retry_count, snapshot_id))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to mark snapshot as failed: {e}")
            return False

    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM snapshot_queue WHERE status = 'pending'")
                pending_count = cursor.fetchone()[0]

                cursor.execute("SELECT SUM(file_size_bytes) FROM snapshot_queue WHERE status = 'pending'")
                total_size = cursor.fetchone()[0] or 0

                cursor.execute("SELECT MAX(uploaded_at) FROM snapshot_queue WHERE status = 'uploaded'")
                last_uploaded = cursor.fetchone()[0]

                return {
                    "pending_count": pending_count,
                    "pending_size_bytes": total_size,
                    "last_uploaded_at": last_uploaded
                }

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"pending_count": 0, "pending_size_bytes": 0, "last_uploaded_at": None}

    def set_status(self, key: str, value: str) -> bool:
        """Set agent status value."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO agent_status (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to set status: {e}")
            return False

    def get_status(self, key: str) -> Optional[str]:
        """Get agent status value."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM agent_status WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else None

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return None

    def cleanup_old_records(self, days: int = 30) -> bool:
        """Delete old uploaded snapshots (cleanup)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM snapshot_queue
                    WHERE status = 'uploaded'
                    AND datetime(uploaded_at) < datetime('now', '-' || ? || ' days')
                """, (days,))
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted} old records")
                return True

        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return False
