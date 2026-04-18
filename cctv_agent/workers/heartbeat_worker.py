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
            
            # Initial local status write
            try:
                self._write_local_status({}, {})
            except:
                pass

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
        """Send heartbeat to backend and write local status."""
        try:
            config = self.config_manager.config
            api_url = config.get("api_url", "http://localhost:8765")
            api_key = config.get("api_key", "")

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

            # Write local status for Tray App
            self._write_local_status(camera_statuses, system_metrics)

            if not api_key:
                return

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
                data = response.json()

            # Sync camera settings
            if "cameras" in data:
                self._sync_cameras(data["cameras"])

        except Exception as e:
            logger.warning(f"Heartbeat report issue: {e}")

    def _write_local_status(self, camera_statuses, system_metrics, error=None):
        """Write a simple status.json for the Tray Icon app."""
        try:
            import json
            from cctv_agent import config as agent_config
            status_file = agent_config.DATA_DIR / "status.json"
            
            is_capturing = any(s["status"] == "online" for s in camera_statuses.values())
            
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "status": "running" if is_capturing else "stopped",
                "camera_count": len(camera_statuses),
                "online_count": sum(1 for s in camera_statuses.values() if s["status"] == "online"),
                "cpu": system_metrics.get("cpu_percent", 0),
                "mem": system_metrics.get("memory_percent", 0),
                "last_error": error
            }
            
            with open(status_file, "w") as f:
                json.dump(status_data, f)
        except Exception as e:
            logger.error(f"Failed to write local status: {e}")

    def _sync_cameras(self, cameras):
        """Update snapshot workers with latest settings."""
        for cam_data in cameras:
            cam_id = cam_data.get("id")
            if cam_id in self.snapshot_workers:
                worker = self.snapshot_workers[cam_id]
                new_interval = cam_data.get("snapshot_interval_seconds", 300)
                if worker.interval_seconds != new_interval:
                    worker.interval_seconds = new_interval
