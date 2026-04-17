"""
Session Management — tracks login/logout boundaries and session IDs
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from desktop.config import DATA_DIR

SESSION_BOUNDARIES_FILE = DATA_DIR / "session_boundaries.json"

class SessionManager:
    """Manages session lifecycle and boundaries"""

    def __init__(self):
        self.session_id = None
        self.user_id = None
        self.username = None
        self.device_id = None
        self.login_time = None
        self.logout_time = None

    def start_session(self, user_id, username, device_id):
        """
        Start a new session when user logs in.
        Args:
            user_id: UUID of the user
            username: Username string
            device_id: Device identifier (hostname-random_hex)
        """
        # Generate session_id: login_{timestamp}_{random_hex}
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        random_hex = uuid.uuid4().hex[:8]
        self.session_id = f"login_{timestamp}_{random_hex}"

        self.user_id = user_id
        self.username = username
        self.device_id = device_id
        self.login_time = datetime.utcnow().isoformat() + "Z"
        self.logout_time = None

        print(f"Session started: {self.session_id} for user {username}")

    def end_session(self):
        """Mark session as ended and write boundary to file"""
        if not self.session_id:
            print("No active session to end")
            return

        self.logout_time = datetime.utcnow().isoformat() + "Z"
        self._write_boundary()
        print(f"Session ended: {self.session_id}")

    def get_session_id(self):
        """Get current session ID"""
        return self.session_id

    def _write_boundary(self):
        """Write session boundary to session_boundaries.json"""
        if not self.session_id:
            return

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            # Load existing boundaries
            boundaries = []
            if SESSION_BOUNDARIES_FILE.exists():
                try:
                    with open(SESSION_BOUNDARIES_FILE, 'r') as f:
                        boundaries = json.load(f)
                except Exception as e:
                    print(f"Error reading session boundaries: {e}")

            # Append new boundary
            boundary = {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "username": self.username,
                "device_id": self.device_id,
                "login_time": self.login_time,
                "logout_time": self.logout_time
            }
            boundaries.append(boundary)

            # Write back to file
            with open(SESSION_BOUNDARIES_FILE, 'w') as f:
                json.dump(boundaries, f, indent=2)

            print(f"Session boundary written for {self.session_id}")
        except Exception as e:
            print(f"Error writing session boundary: {e}")


# Global singleton
_session_manager = None

def get_session_manager():
    """Get or create global SessionManager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
