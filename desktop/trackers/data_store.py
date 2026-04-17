"""
Thread-safe data store for real-time tracking metrics.
Shared between trackers and the dashboard UI.
"""
import threading
from datetime import datetime
from pathlib import Path
from desktop.config import LOGS_DIR


class ActivityDataStore:
    """Global thread-safe store for tracker data."""

    def __init__(self):
        self.lock = threading.Lock()

        # Live tracking data
        self.active_window = "Idle"
        self.keystrokes_current = 0
        self.clicks_current = 0
        self.window_sessions = 0

        # Daily totals
        self.keystrokes_today = 0
        self.clicks_today = 0

        # Sync status
        self.last_upload_time = None
        self.last_upload_status = "pending"  # pending, success, failed

        # Tracker status
        self.is_paused = False

    def set_active_window(self, window_title: str):
        """Update currently active window."""
        with self.lock:
            self.active_window = window_title or "Idle"

    def add_keystroke(self):
        """Increment keystroke counter."""
        with self.lock:
            self.keystrokes_current += 1
            self.keystrokes_today += 1

    def add_click(self):
        """Increment click counter."""
        with self.lock:
            self.clicks_current += 1
            self.clicks_today += 1

    def add_window_session(self):
        """Increment window session counter."""
        with self.lock:
            self.window_sessions += 1

    def reset_live_counts(self):
        """Reset live counters (called periodically)."""
        with self.lock:
            self.keystrokes_current = 0
            self.clicks_current = 0

    def reset_daily_counts(self):
        """Reset daily counters (called at midnight)."""
        with self.lock:
            self.keystrokes_today = 0
            self.clicks_today = 0
            self.window_sessions = 0

    def set_upload_status(self, status: str, timestamp=None):
        """Update upload status (success, failed, pending)."""
        with self.lock:
            self.last_upload_status = status
            if timestamp:
                self.last_upload_time = timestamp
            else:
                self.last_upload_time = datetime.now()

    def set_paused(self, paused: bool):
        """Update pause state."""
        with self.lock:
            self.is_paused = paused

    def get_snapshot(self) -> dict:
        """Get a snapshot of all data (thread-safe)."""
        with self.lock:
            return {
                "active_window": self.active_window,
                "keystrokes_current": self.keystrokes_current,
                "clicks_current": self.clicks_current,
                "window_sessions": self.window_sessions,
                "keystrokes_today": self.keystrokes_today,
                "clicks_today": self.clicks_today,
                "last_upload_time": self.last_upload_time,
                "last_upload_status": self.last_upload_status,
                "is_paused": self.is_paused,
            }

    def load_daily_totals_from_log(self):
        """Load today's totals from the JSON log file."""
        import json
        from datetime import datetime as dt

        today = dt.now().strftime("%Y-%m-%d")
        log_file = LOGS_DIR / f"{today}.json"

        if not log_file.exists():
            return

        try:
            with open(log_file, "r") as f:
                entries = json.load(f)

            keystrokes = 0
            clicks = 0
            sessions = 0

            for entry in entries:
                if entry.get("event_type") == "input_summary":
                    data = entry.get("data", {})
                    keystrokes += data.get("keystrokes", 0)
                    clicks += data.get("mouse_clicks", 0)
                elif entry.get("event_type") == "window_change":
                    sessions += 1

            with self.lock:
                self.keystrokes_today = keystrokes
                self.clicks_today = clicks
                self.window_sessions = sessions
        except Exception as e:
            print(f"Error loading daily totals: {e}")


# Global instance
_data_store = None

def get_data_store() -> ActivityDataStore:
    """Get or create the global data store."""
    global _data_store
    if _data_store is None:
        _data_store = ActivityDataStore()
    return _data_store
