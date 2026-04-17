import os
import sys
from pathlib import Path

# Paths — handle PyInstaller bundled exe vs dev mode
if getattr(sys, 'frozen', False):
    # Running as PyInstaller exe: dist/ProMe.exe → parent.parent = project root
    BASE_DIR = Path(sys.executable).resolve().parent.parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"

# Ensure directories exist
for d in [DATA_DIR, LOGS_DIR, SCREENSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Configuration
SCREENSHOT_INTERVAL = 300  # 5 minutes
INPUT_SUMMARY_INTERVAL = 60  # 1 minute
TELEMETRY_INTERVAL = 60  # 1 minute
WINDOW_POLL_INTERVAL = 5  # 5 seconds

# App Info
APP_NAME = "ProMe"
VERSION = "0.1.0"
ICON_PATH = str(BASE_DIR / "desktop" / "assets" / "icon.png")

# API Config
API_URL = "http://34.63.62.95"
