"""
Server Uploader — pushes locally accumulated logs and screenshots
to the ProMe backend API. Includes offline queue + retry logic.
"""
import time
import json
import threading
import requests
from pathlib import Path
from datetime import datetime
from desktop.config import API_URL, LOGS_DIR, SCREENSHOTS_DIR
from desktop.trackers.data_store import get_data_store

UPLOAD_INTERVAL = 60  # seconds between upload attempts
MAX_RETRY_BACKOFF = 300  # 5 minutes max backoff


def get_or_create_device_id() -> str:
    """Get or create device ID (globally unique for this machine)"""
    config_path = Path(LOGS_DIR).parent / "device_id.txt"
    if config_path.exists():
        return config_path.read_text().strip()
    import secrets, platform
    device_id = f"{platform.node()}-{secrets.token_hex(4)}"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(device_id)
    return device_id


class ServerUploader:
    def __init__(self, auth_token=None, user_id=None):
        self.device_id = get_or_create_device_id()
        self.auth_token = auth_token
        self.user_id = user_id
        self.uploaded_screenshots = self._load_uploaded_set()
        self._consecutive_failures = 0
        self._uploaded_count = self._load_uploaded_count()  # persisted to disk
        self.lock = threading.Lock()
        self.data_store = get_data_store()

    def _uploaded_set_path(self) -> Path:
        return Path(LOGS_DIR).parent / "uploaded_screenshots.json"

    def _load_uploaded_set(self) -> set:
        """Load the set of already-uploaded screenshot filenames from disk."""
        path = self._uploaded_set_path()
        if path.exists():
            try:
                with open(path, "r") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def _save_uploaded_set(self):
        """Persist the uploaded set to disk so it survives restarts."""
        path = self._uploaded_set_path()
        try:
            with open(path, "w") as f:
                json.dump(list(self.uploaded_screenshots), f)
        except Exception as e:
            print(f"Warning: could not save uploaded set: {e}")

    def _uploaded_count_path(self) -> Path:
        return Path(LOGS_DIR).parent / "uploaded_log_counts.json"

    def _load_uploaded_count(self) -> dict:
        """Load the count of already-uploaded log entries per day from disk."""
        path = self._uploaded_count_path()
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_uploaded_count(self):
        """Persist the uploaded count to disk so it survives restarts."""
        path = self._uploaded_count_path()
        try:
            with open(path, "w") as f:
                json.dump(self._uploaded_count, f)
        except Exception as e:
            print(f"Warning: could not save uploaded count: {e}")

    def _server_reachable(self) -> bool:
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            r = requests.post(
                f"{API_URL}/api/telemetry/heartbeat",
                json={"device_id": self.device_id, "user_id": self.user_id},
                headers=headers,
                timeout=5,
            )
            return r.status_code == 200
        except Exception:
            return False

    def _upload_logs(self):
        """Upload only NEW log entries that haven't been sent yet."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOGS_DIR / f"{today}.json"

        if not log_file.exists():
            return

        with self.lock:
            try:
                with open(log_file, "r") as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, Exception):
                return

        if not entries:
            return

        # Only upload entries we haven't sent yet
        already_sent = self._uploaded_count.get(today, 0)
        new_entries = entries[already_sent:]

        if not new_entries:
            return

        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            r = requests.post(
                f"{API_URL}/api/telemetry/logs",
                json={"device_id": self.device_id, "user_id": self.user_id, "entries": new_entries},
                headers=headers,
                timeout=15,
            )
            if r.status_code == 200:
                self._uploaded_count[today] = len(entries)
                self._save_uploaded_count()
                print(f"Uploaded {len(new_entries)} new log entries ({len(entries)} total today).")
                self._consecutive_failures = 0
                self.data_store.set_upload_status("success")
            else:
                print(f"Log upload returned {r.status_code}")
                self._consecutive_failures += 1
                self.data_store.set_upload_status("failed")
        except Exception as e:
            print(f"Log upload failed: {e}")
            self._consecutive_failures += 1
            self.data_store.set_upload_status("failed")

    def _get_captured_at_for_screenshot(self, filename: str) -> str:
        """Extract captured_at timestamp from the log entry matching this screenshot."""
        try:
            import re
            # Extract date from filename — handles both formats:
            #   "2026-04-13_14-36-07.png"  (local, no device_id)
            #   "Mohit-7b969fed_2026-04-13_14-36-07.png"  (with device_id)
            match = re.search(r'(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}-\d{2}', filename)
            if not match:
                return None

            date_str = match.group(1)
            log_file = LOGS_DIR / f"{date_str}.json"

            if not log_file.exists():
                return None

            with self.lock:
                try:
                    with open(log_file, "r") as f:
                        entries = json.load(f)
                except (json.JSONDecodeError, Exception):
                    return None

            # Find the screenshot event with matching filename
            for entry in entries:
                if entry.get("event_type") == "screenshot":
                    data = entry.get("data", {})
                    if data.get("filename") == filename:
                        return data.get("captured_at")

            # Fallback: extract timestamp directly from filename
            time_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})', filename)
            if time_match:
                d, h, m, s = time_match.group(1), time_match.group(2), time_match.group(3), time_match.group(4)
                return f"{d}T{h}:{m}:{s}"

            return None
        except Exception as e:
            print(f"Error extracting captured_at for {filename}: {e}")
            return None

    def _upload_screenshots(self):
        """Upload new screenshots that haven't been sent yet."""
        if not SCREENSHOTS_DIR.exists():
            return

        files = list(SCREENSHOTS_DIR.glob("*.png"))
        # Only upload locally-captured screenshots (no device_id prefix).
        # Server-saved files have format: DeviceName-hex_YYYY-MM-DD_HH-MM-SS.png
        # Local files have format: YYYY-MM-DD_HH-MM-SS.png
        local_files = [f for f in files if f.name[0:4].isdigit()]
        new_files = [f for f in local_files if f.name not in self.uploaded_screenshots]

        uploaded_any = False
        for filepath in new_files[-5:]:  # Max 5 per batch
            try:
                # Get the captured_at timestamp from logs
                captured_at = self._get_captured_at_for_screenshot(filepath.name)

                with open(filepath, "rb") as img:
                    headers = {}
                    if self.auth_token:
                        headers["Authorization"] = f"Bearer {self.auth_token}"

                    # Build data with device_id, user_id, and optionally captured_at
                    data = {"device_id": self.device_id, "user_id": self.user_id}
                    if captured_at:
                        data["captured_at"] = captured_at

                    r = requests.post(
                        f"{API_URL}/api/telemetry/screenshot",
                        files={"file": (filepath.name, img, "image/png")},
                        data=data,
                        headers=headers,
                        timeout=30,
                    )
                    if r.status_code == 200:
                        self.uploaded_screenshots.add(filepath.name)
                        uploaded_any = True
                        print(f"Uploaded screenshot: {filepath.name}")
                    else:
                        print(f"Screenshot upload returned {r.status_code}")
            except Exception as e:
                print(f"Screenshot upload failed for {filepath.name}: {e}")

        if uploaded_any:
            self._save_uploaded_set()

    def run(self, stop_event, pause_event=None):
        print("Server Uploader started.")
        while not stop_event.is_set():
            # Respect pause state
            if pause_event and pause_event.is_set():
                time.sleep(5)
                continue

            # Calculate backoff
            interval = min(
                UPLOAD_INTERVAL * (2 ** self._consecutive_failures),
                MAX_RETRY_BACKOFF,
            )

            if self._server_reachable():
                self._upload_logs()
                self._upload_screenshots()
            else:
                print(f"Server unreachable. Retrying in {interval}s...")
                self._consecutive_failures += 1
                self.data_store.set_upload_status("pending")

            # Wait, checking stop_event frequently
            for _ in range(int(interval)):
                if stop_event.is_set():
                    break
                time.sleep(1)
