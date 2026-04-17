import time
import threading
from pynput import keyboard, mouse
from desktop.storage.logger import logger
from desktop.config import INPUT_SUMMARY_INTERVAL
from desktop.trackers.data_store import get_data_store
from desktop.trackers.live_feed import get_live_feed
from desktop.trackers.session_manager import get_session_manager

class InputTracker:
    def __init__(self):
        self.keystrokes = 0
        self.mouse_clicks = 0
        self.mouse_distance = 0
        self.last_mouse_pos = None
        self.lock = threading.Lock()
        self.data_store = get_data_store()
        self.live_feed = get_live_feed()

    def on_press(self, key):
        with self.lock:
            self.keystrokes += 1
        self.data_store.add_keystroke()

        # Log individual keystroke to live feed (no key content, just count)
        self.live_feed.add_event("keystroke", {"key": "key_press"})

    def on_click(self, x, y, button, pressed):
        if pressed:
            with self.lock:
                self.mouse_clicks += 1
            self.data_store.add_click()

            # Log individual click to live feed
            btn_name = str(button).replace("Button.", "")
            self.live_feed.add_event("mouse_click", {
                "button": btn_name, "x": x, "y": y
            })

    def on_move(self, x, y):
        with self.lock:
            if self.last_mouse_pos:
                dist = ((x - self.last_mouse_pos[0])**2 + (y - self.last_mouse_pos[1])**2)**0.5
                self.mouse_distance += dist
            self.last_mouse_pos = (x, y)

    def run(self, stop_event, pause_event=None):
        print("Input Tracker started.")

        k_listener = keyboard.Listener(on_press=self.on_press)
        m_listener = mouse.Listener(on_click=self.on_click, on_move=self.on_move)

        k_listener.start()
        m_listener.start()

        while not stop_event.is_set():
            time.sleep(INPUT_SUMMARY_INTERVAL)

            if pause_event and pause_event.is_set():
                continue

            with self.lock:
                data = {
                    "interval_seconds": INPUT_SUMMARY_INTERVAL,
                    "keystrokes": self.keystrokes,
                    "mouse_clicks": self.mouse_clicks,
                    "mouse_distance_px": int(self.mouse_distance)
                }
                self.keystrokes = 0
                self.mouse_clicks = 0
                self.mouse_distance = 0

            session_id = get_session_manager().get_session_id()
            logger.log_event("input_summary", data, session_id=session_id)
            self.data_store.reset_live_counts()

        k_listener.stop()
        m_listener.stop()
