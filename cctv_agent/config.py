"""CCTV Agent configuration."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path.home() / "CCTVAgent"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
QUEUE_DIR = DATA_DIR / "queue"

# Ensure directories exist
BASE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

# Config file
CONFIG_FILE = BASE_DIR / "config.json"

# Database
DB_FILE = BASE_DIR / "cctv_agent.db"

# Signal/control files
FORCE_UPLOAD_FILE = DATA_DIR / "FORCE_UPLOAD"
LOGS_JSONL_FILE = DATA_DIR / "logs.jsonl"

# Defaults
DEFAULT_SNAPSHOT_INTERVAL = 300  # 5 minutes
DEFAULT_JPEG_QUALITY = 85
DEFAULT_RESOLUTION_PROFILE = "sub"
HEARTBEAT_INTERVAL = 30  # seconds
DISCOVERY_INTERVAL = 600  # 10 minutes
UPLOAD_BATCH_INTERVAL = 3600  # 1 hour
UPLOAD_RETRY_MAX = 3
UPLOAD_RETRY_BACKOFF_BASE = 60  # seconds

# API
API_URL = os.getenv("CCTV_API_URL", "http://34.63.62.95")
AGENT_API_KEY = os.getenv("CCTV_AGENT_API_KEY", "")

# GCS
GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "")
GCS_PROJECT = os.getenv("GCS_PROJECT_ID", "")

# Frame capture
FRAME_GRAB_TIMEOUT = 10  # seconds
MAX_RETRY_ATTEMPTS = 5
INITIAL_BACKOFF = 2  # seconds
MAX_BACKOFF = 30  # seconds

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
