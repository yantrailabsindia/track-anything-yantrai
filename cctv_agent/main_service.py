"""
CCTV Agent Headless Service - Main entry point.
Runs in background: capture, upload, heartbeat, discovery.
"""

import logging
import sys
import signal
import threading
import queue
from pathlib import Path

from cctv_agent import config as agent_config
from cctv_agent.core.config_manager import ConfigManager
from cctv_agent.services.db_manager import DBManager
from cctv_agent.services.gcs_uploader import GCSUploader
from cctv_agent.workers.snapshot_worker import SnapshotWorker
from cctv_agent.workers.upload_worker import UploadWorker
from cctv_agent.workers.heartbeat_worker import HeartbeatWorker
from cctv_agent.workers.discovery_worker import DiscoveryWorker
from cctv_agent.workers.log_emitter import LogEmitter

# Setup logging
logging.basicConfig(
    level=agent_config.LOG_LEVEL,
    format=agent_config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(agent_config.LOGS_DIR / "service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CCTVAgentService:
    """Main CCTV agent service."""

    def __init__(self):
        """Initialize the service."""
        self.config_manager = ConfigManager()
        self.db_manager = DBManager(agent_config.DB_FILE)
        self.log_emitter = LogEmitter(agent_config.LOGS_JSONL_FILE)

        self.snapshot_workers = {}
        self.upload_worker = None
        self.heartbeat_worker = None
        self.discovery_worker = None
        self.snapshot_queue = queue.Queue()

        self.stop_event = threading.Event()

    def start(self):
        """Start the service."""
        logger.info("=" * 60)
        logger.info("CCTV Agent Service Starting")
        logger.info("=" * 60)

        try:
            # Initialize GCS uploader
            cloud_settings = self.config_manager.get_cloud_settings()
            gcs_uploader = GCSUploader(
                bucket_name=cloud_settings.get("gcs_bucket"),
                project_id=cloud_settings.get("gcs_project") or None
            )
            logger.info("GCS uploader initialized")

        except Exception as e:
            logger.error(f"Failed to initialize GCS: {e}")
            gcs_uploader = None

        # Start upload worker
        self.upload_worker = UploadWorker(
            self.config_manager,
            self.db_manager,
            self.log_emitter,
            gcs_uploader
        )
        self.upload_worker.start()

        # Start heartbeat worker
        self.heartbeat_worker = HeartbeatWorker(
            self.config_manager,
            self.snapshot_workers,
            self.log_emitter
        )
        self.heartbeat_worker.start()

        # Start discovery worker
        self.discovery_worker = DiscoveryWorker(
            self.config_manager,
            self.log_emitter
        )
        self.discovery_worker.start()

        # Start snapshot workers for each camera
        self._start_snapshot_workers()

        logger.info("Service started successfully")
        self.log_emitter.emit("info", "service", "CCTV Agent service started")

    def _start_snapshot_workers(self):
        """Start a snapshot worker for each configured camera."""
        cameras = self.config_manager.get_cameras()

        for i, camera in enumerate(cameras, start=1):
            if not camera.get("is_active", True):
                continue

            ip_address = camera.get("ip_address") or camera.get("ip")
            camera_id = camera.get("id") or ip_address
            location_id = camera.get("location_id", "unknown")

            # Get RTSP URL with fallback to channels
            rtsp_url = camera.get("rtsp_url")
            if not rtsp_url and camera.get("channels"):
                # Use first enabled channel as fallback
                for channel in camera.get("channels"):
                    if channel.get("enabled", True):
                        rtsp_url = channel.get("sub_stream_uri")
                        break

            # Check if camera has an explicit 'number' in config, else use index
            camera_number = camera.get("number", i)

            worker = SnapshotWorker(
                camera_id=camera_id,
                location_id=location_id,
                org_id=self.config_manager.config.get("org_id", "unknown"),
                ip_address=ip_address,
                rtsp_url=rtsp_url or "",
                interval_seconds=camera.get("snapshot_interval_seconds", 300),
                jpeg_quality=camera.get("jpeg_quality", 85),
                snapshot_queue=self.snapshot_queue,
                log_emitter=self.log_emitter,
                db_manager=self.db_manager,
                camera_number=camera_number
            )
            worker.start()
            self.snapshot_workers[camera_id] = worker
            logger.info(f"Started snapshot worker for camera {camera_id}")

    def stop(self):
        """Stop the service."""
        logger.info("Shutting down service...")
        self.stop_event.set()

        # Stop all workers
        for worker in self.snapshot_workers.values():
            worker.stop()

        if self.upload_worker:
            self.upload_worker.stop()
        if self.heartbeat_worker:
            self.heartbeat_worker.stop()
        if self.discovery_worker:
            self.discovery_worker.stop()

        logger.info("Service stopped")
        self.log_emitter.emit("info", "service", "CCTV Agent service stopped")

    def run(self):
        """Run the service (blocking)."""
        self.start()

        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep running
        try:
            while not self.stop_event.is_set():
                self.stop_event.wait(1)
        except KeyboardInterrupt:
            self.stop()


def main():
    """Entry point."""
    service = CCTVAgentService()
    service.run()


if __name__ == "__main__":
    main()
