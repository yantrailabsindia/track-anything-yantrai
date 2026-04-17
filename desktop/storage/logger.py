import json
import threading
from datetime import datetime
from desktop.config import LOGS_DIR

class Logger:
    _lock = threading.Lock()

    @staticmethod
    def log_event(event_type, data, session_id=None):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "data": data
        }

        # Include session_id if provided
        if session_id:
            log_entry["session_id"] = session_id

        filename = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"

        with Logger._lock:
            try:
                if filename.exists():
                    with open(filename, "r+") as f:
                        try:
                            logs = json.load(f)
                        except json.JSONDecodeError:
                            logs = []
                        logs.append(log_entry)
                        f.seek(0)
                        json.dump(logs, f, indent=2)
                        f.truncate()
                else:
                    with open(filename, "w") as f:
                        json.dump([log_entry], f, indent=2)
            except Exception as e:
                print(f"Error logging event: {e}")

logger = Logger()
