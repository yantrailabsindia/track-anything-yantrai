import time
import pygetwindow as gw
import psutil
from desktop.storage.logger import logger
from desktop.config import WINDOW_POLL_INTERVAL
from desktop.trackers.data_store import get_data_store
from desktop.trackers.live_feed import get_live_feed
from desktop.trackers.session_manager import get_session_manager

class WindowTracker:
    def __init__(self):
        self.last_window = None
        self.start_time = time.time()
        self.data_store = get_data_store()
        self.live_feed = get_live_feed()

    def get_active_window_info(self):
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                window_title = active_window.title
                return window_title
        except Exception as e:
            print(f"Error getting window info: {e}")
        return None

    def run(self, stop_event, pause_event=None):
        print("Window Tracker started.")
        while not stop_event.is_set():
            if pause_event and pause_event.is_set():
                time.sleep(1)
                continue

            current_window = self.get_active_window_info()
            if current_window:
                self.data_store.set_active_window(current_window)

            if current_window != self.last_window:
                now = time.time()
                duration = int(now - self.start_time)

                if self.last_window:
                    session_id = get_session_manager().get_session_id()
                    logger.log_event("window_change", {
                        "window_title": self.last_window,
                        "duration_seconds": duration
                    }, session_id=session_id)
                    self.data_store.add_window_session()
                    self.live_feed.add_event("window_change", {
                        "window_title": self.last_window,
                        "new_window": current_window or "Unknown",
                        "duration_seconds": duration
                    })

                self.last_window = current_window
                self.start_time = now

            time.sleep(WINDOW_POLL_INTERVAL)
