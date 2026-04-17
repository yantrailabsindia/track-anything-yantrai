"""
Emits log events to a shared JSONL file for GUI consumption.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LogEmitter:
    """Writes events to JSONL log file."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        level: str,
        event: str,
        message: str,
        camera_id: Optional[str] = None,
        **kwargs
    ):
        """
        Emit a log event.

        Args:
            level: info, warning, error
            event: capture, upload, discovery, etc.
            message: Human-readable message
            camera_id: Optional camera ID
            **kwargs: Additional fields
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "event": event,
            "message": message
        }
        if camera_id:
            log_entry["camera_id"] = camera_id
        log_entry.update(kwargs)

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to emit log: {e}")

    def get_recent(self, count: int = 10) -> list:
        """Get last N log entries."""
        if not self.log_file.exists():
            return []

        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                entries = []
                for line in lines[-count:]:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
                return entries
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
            return []
