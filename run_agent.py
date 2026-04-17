"""
ProMe Desktop Agent — Standalone entry point for PyInstaller.
"""
import sys
import os

# Ensure the parent directory is in the path so imports work
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Override config paths so they're relative to the exe location
import desktop.config as config
config.BASE_DIR = __import__('pathlib').Path(BASE_DIR)
config.DATA_DIR = config.BASE_DIR / "data"
config.LOGS_DIR = config.DATA_DIR / "logs"
config.SCREENSHOTS_DIR = config.DATA_DIR / "screenshots"
for d in [config.DATA_DIR, config.LOGS_DIR, config.SCREENSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

from desktop.main import main
main()
