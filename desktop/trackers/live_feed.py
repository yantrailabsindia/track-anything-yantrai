"""
Live event feed for real-time dashboard display.
Accumulates events in memory and flushes to disk periodically
to avoid I/O contention on every keystroke.
"""
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from desktop.config import DATA_DIR

LIVE_FEED_FILE = DATA_DIR / "live_feed.json"
MAX_EVENTS = 200
FLUSH_INTERVAL = 0.5  # Write to disk every 500ms


class LiveFeed:
    """Thread-safe live event feed with periodic disk flush."""

    def __init__(self):
        self.lock = threading.Lock()
        self._events = []
        self._dirty = False

        # Load existing events on startup
        try:
            if LIVE_FEED_FILE.exists():
                with open(LIVE_FEED_FILE, "r") as f:
                    self._events = json.load(f)
                self._events = self._events[-MAX_EVENTS:]
        except Exception:
            self._events = []

        # Start background flush thread
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def add_event(self, event_type: str, data: dict):
        """Add a single event to the live feed (fast, memory only)."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        with self.lock:
            self._events.append(event)
            if len(self._events) > MAX_EVENTS:
                self._events = self._events[-MAX_EVENTS:]
            self._dirty = True

    def _flush_loop(self):
        """Periodically write accumulated events to disk."""
        while True:
            time.sleep(FLUSH_INTERVAL)
            with self.lock:
                if not self._dirty:
                    continue
                self._dirty = False
                snapshot = list(self._events)
            try:
                tmp_file = LIVE_FEED_FILE.with_suffix(".tmp")
                with open(tmp_file, "w") as f:
                    json.dump(snapshot, f)
                tmp_file.replace(LIVE_FEED_FILE)
            except Exception:
                pass

    def get_events(self) -> list:
        """Read events (thread-safe)."""
        with self.lock:
            return list(self._events)


# Global instance
_live_feed = None


def get_live_feed() -> LiveFeed:
    global _live_feed
    if _live_feed is None:
        _live_feed = LiveFeed()
    return _live_feed
