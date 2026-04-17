"""
Heartbeat worker - periodic status report to backend.
"""

import threading
import logging
import time
import psutil
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class HeartbeatWorker:
    """Sends periodic heartbeat + telemetry to backend."""

    def __init__(
        self,
        config_manager,
        snapshot_workers: dict,
        log_emitter,
        interval_seconds: int = 30
    ):
        """
        Initialize heartbeat worker.

        Args:
            config_manager: ConfigManager instance
            snapshot_workers: Dict of {camera_id: SnapshotWorker}
            log_emitter: LogEmitter instance
            interval_seconds: Heartbeat interval (default 30s)
        """
        self.config_manager = config_manager
        self.snapshot_workers = snapshot_workers
        self.log_emitter = log_emitter
        self.interval_seconds = interval_seconds

        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        """Start the heartbeat thread."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("Started heartbeat worker")

    def stop(self):
        """Stop the heartbeat thread."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            logger.info("Stopped heartbeat worker")

    def _run(self):
        """Main heartbeat loop."""
        while not self.stop_event.is_set():
            self._send_heartbeat()
            self.stop_event.wait(self.interval_seconds)

    def _send_heartbeat(self):
        """Send heartbeat to backend."""
        try:
            config = self.config_manager.config
            api_url = config.get("api_url", "http://localhost:8765")
            api_key = config.get("api_key", "")

            if not api_key:
                logger.debug("No API key configured, skipping heartbeat")
                return

            # Collect camera statuses
            camera_statuses = {}
            for camera_id, worker in self.snapshot_workers.items():
                status = worker.get_status()
                camera_statuses[camera_id] = {
                    "status": "online" if status["is_running"] else "offline",
                    "last_capture": status["last_capture_time"],
                    "last_error": status["last_error"]
                }

            # Collect system metrics
            system_metrics = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent
            }

            payload = {
                "agent_id": config.get("agent_id", "unknown"),
                "camera_statuses": camera_statuses,
                "system_metrics": system_metrics
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{api_url}/api/cctv/agent/heartbeat",
                    json=payload,
                    params={"api_key": api_key}
                )
                response.raise_for_status()

            logger.debug(f"Heartbeat sent: {len(camera_statuses)} cameras")

        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
