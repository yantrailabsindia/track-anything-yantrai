"""
ProMe macOS Agent (Apple Silicon Optimized)
-------------------------------------------
Note: This script requires 'pyobjc' to be installed for native window tracking.
Usage: pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa pynput mss psutil requests
"""

import os
import time
import json
import threading
from datetime import datetime
from pathlib import Path

# macOS Specific Imports
try:
    from AppKit import NSWorkspace
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID
    )
except ImportError:
    print("Error: pyobjc-frameworks not found. Run 'pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa'")

import psutil
from mss import mss
from pynput import mouse, keyboard
import requests

# CONFIGURATION
BACKEND_URL = "http://localhost:8765"  # Shift to your cloud URL later
SCREENSHOT_INTERVAL = 300  # 5 minutes
TELEMETRY_INTERVAL = 10    # 10 seconds
DATA_DIR = Path.home() / ".prome"
DATA_DIR.mkdir(exist_ok=True)

class ProMeMacAgent:
    def __init__(self):
        self.running = True
        self.keystrokes = 0
        self.clicks = 0
        self.current_window = ""
        self.last_screenshot_time = 0
        self.setup_listeners()

    def get_active_window(self):
        """macOS Native Window Tracking via Quartz."""
        try:
            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if not app:
                return "Unknown"
            
            app_name = app.localizedName()
            
            # Get only on-screen windows
            options = kCGWindowListOptionOnScreenOnly
            window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID) or []
            
            for window in window_list:
                if window.get('kCGWindowOwnerName') == app_name:
                    # kCGWindowName might be missing for some apps due to permissions
                    title = window.get('kCGWindowName', 'Active App')
                    return f"{app_name} - {title}"
            
            return app_name
        except Exception:
            return "Unknown (Check Permissions)"

    def on_press(self, key):
        self.keystrokes += 1

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.clicks += 1

    def setup_listeners(self):
        self.kb_listener = keyboard.Listener(on_press=self.on_press)
        self.m_listener = mouse.Listener(on_click=self.on_click)
        self.kb_listener.start()
        self.m_listener.start()

    def take_screenshot(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = DATA_DIR / filename
            
            with mss() as sct:
                sct.shot(output=str(filepath))
            
            # Send to backend
            with open(filepath, "rb") as f:
                requests.post(f"{BACKEND_URL}/api/screenshots/", files={"file": f})
            
            # Clean up local file
            os.remove(filepath)
        except Exception as e:
            print(f"Screenshot failed: {e}")

    def send_telemetry(self):
        try:
            new_window = self.get_active_window()
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "user_id": "mac-user-001", # Should be from config/auth
                "event_type": "telemetry",
                "data": {
                    "active_window": new_window,
                    "keystrokes": self.keystrokes,
                    "clicks": self.clicks,
                    "cpu_usage": psutil.cpu_percent(),
                    "ram_usage": psutil.virtual_memory().percent
                }
            }
            
            requests.post(f"{BACKEND_URL}/api/activity/", json=data)
            
            # Reset counters
            self.keystrokes = 0
            self.clicks = 0
        except Exception as e:
            print(f"Telemetry failed: {e}")

    def run(self):
        print("ProMe macOS Agent Started.")
        print("Note: If window titles are missing, grant Accessibility permissions to Terminal/App.")
        
        while self.running:
            # Telemetry logic
            self.send_telemetry()
            
            # Screenshot logic
            if time.time() - self.last_screenshot_time >= SCREENSHOT_INTERVAL:
                self.take_screenshot()
                self.last_screenshot_time = time.time()
                
            time.sleep(TELEMETRY_INTERVAL)

if __name__ == "__main__":
    agent = ProMeMacAgent()
    agent.run()
