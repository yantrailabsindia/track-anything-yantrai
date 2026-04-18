"""
Local SQLite database manager for CCTV agent.
Tracks queue status, snapshots, and logs.
"""

import sqlite3
import logging
import json
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
        """
        self.db_path = db_path
        self._init_sqlite()
        self.init_db()

    def _init_sqlite(self):
        """Enable WAL mode once for the database file."""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to set PRAGMA: {e}")

    def _get_connection(self):
        """Get a connection with row_factory and timeout set."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database schema."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS agent_status (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON snapshot_queue(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_camera ON snapshot_queue(camera_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_captured ON snapshot_queue(captured_at)")
                conn.commit()
                logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def add_snapshot_to_queue(self, camera_id, location_id, org_id, captured_at, local_file_path, gcs_path, file_size_bytes, resolution=None, status="pending"):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO snapshot_queue
                    (camera_id, location_id, org_id, captured_at, local_file_path, gcs_path, file_size_bytes, resolution, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (camera_id, location_id, org_id, captured_at.isoformat(), local_file_path, gcs_path, file_size_bytes, resolution, status))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add snapshot to queue: {e}")
            return False

    def get_pending_snapshots(self, limit=100, max_retries=3):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM snapshot_queue
                    WHERE status = 'pending' OR (status = 'failed' AND retry_count < ?)
                    ORDER BY captured_at ASC
                    LIMIT ?
                """, (max_retries, limit))
                rows = cursor.fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get pending snapshots: {e}")
            return []

    def get_ripe_snapshots(self, buffer_minutes=10, limit=500):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM snapshot_queue 
                    WHERE status = 'pending' 
                    AND datetime(captured_at) < datetime('now', '-' || ? || ' minutes')
                    ORDER BY captured_at ASC
                    LIMIT ?
                """, (buffer_minutes, limit))
                rows = cursor.fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to get ripe snapshots: {e}")
            return []

    def _row_to_dict(self, row):
        """Manually convert sqlite3.Row to dict to avoid sequence errors."""
        try:
            return {k: row[k] for k in row.keys()}
        except Exception as e:
            # Fallback if keys/row are weird
            logger.error(f"Row conversion error: {e}")
            return {}

    def mark_uploaded(self, snapshot_id):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE snapshot_queue SET status = 'uploaded', uploaded_at = CURRENT_TIMESTAMP WHERE id = ?", (snapshot_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed mark_uploaded: {e}")
            return False

    def mark_failed(self, snapshot_id, error, retry_count):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE snapshot_queue SET status = 'failed', last_error = ?, retry_count = ? WHERE id = ?", (error, retry_count, snapshot_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed mark_failed: {e}")
            return False

    def get_queue_stats(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM snapshot_queue WHERE status = 'pending'")
                pending_count = cursor.fetchone()[0]
                return {"pending_count": pending_count}
        except:
            return {"pending_count": 0}

    def set_status(self, key, value):
        try:
            with self._get_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO agent_status (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (key, value))
                conn.commit()
                return True
        except:
            return False

    def get_status(self, key):
        try:
            with self._get_connection() as conn:
                row = conn.execute("SELECT value FROM agent_status WHERE key = ?", (key,)).fetchone()
                return row[0] if row else None
        except:
            return None

    def get_last_capture_time(self, camera_id):
        try:
            with self._get_connection() as conn:
                row = conn.execute("SELECT captured_at FROM snapshot_queue WHERE camera_id = ? ORDER BY captured_at DESC LIMIT 1", (camera_id,)).fetchone()
                return datetime.fromisoformat(row[0]) if row else None
        except:
            return None

    def cleanup_local_file_after_upload(self, snapshot_id, local_file_path):
        if self.mark_uploaded(snapshot_id):
            try:
                from cctv_agent import config as agent_config
                full_path = agent_config.QUEUE_DIR / local_file_path.replace("queue/", "")
                if full_path.exists():
                    full_path.unlink()
                return True
            except:
                return True
        return False

    def cleanup_old_records(self, days=30):
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM snapshot_queue WHERE status = 'uploaded' AND datetime(uploaded_at) < datetime('now', '-' || ? || ' days')", (days,))
                conn.commit()
                return True
        except:
            return False
