import time
from datetime import datetime
from desktop.storage.logger import logger
from desktop.config import SCREENSHOTS_DIR, SCREENSHOT_INTERVAL
from desktop.trackers.session_manager import get_session_manager

# Try to import mss, but continue if not available
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("WARNING: mss module not available - screenshots disabled")

class ScreenshotTracker:
    def run(self, stop_event, pause_event=None):
        if not MSS_AVAILABLE:
            print("Screenshot Tracker disabled (mss not available).")
            # Keep the thread alive but do nothing
            while not stop_event.is_set():
                time.sleep(1)
            return

        print("Screenshot Tracker started.")
        try:
            with mss.mss() as sct:
                while not stop_event.is_set():
                    if pause_event and pause_event.is_set():
                        time.sleep(1)
                        continue

                    # Capture timestamp BEFORE capture (when user action happened)
                    capture_time = datetime.now()
                    filename = f"{capture_time.strftime('%Y-%m-%d_%H-%M-%S')}.png"
                    filepath = SCREENSHOTS_DIR / filename

                    try:
                        # Capture primary monitor
                        sct.shot(output=str(filepath))

                        session_id = get_session_manager().get_session_id()
                        logger.log_event("screenshot", {
                            "filename": filename,
                            "path": str(filepath),
                            "captured_at": capture_time.isoformat()
                        }, session_id=session_id)
                    except Exception as e:
                        print(f"Error capturing screenshot: {e}")

                    # Wait for interval, checking stop_event frequently
                    for _ in range(SCREENSHOT_INTERVAL):
                        if stop_event.is_set():
                            break
                        time.sleep(1)
        except Exception as e:
            print(f"Screenshot tracker error: {e}")
