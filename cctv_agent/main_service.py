"""
CCTV Agent Headless Service - Main entry point.
Runs in background: capture, upload, heartbeat, discovery.
"""

import logging
import signal
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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

        # Service 2 & 3: Tunnel Uploader & Cleanup (Delayed by 10 mins)
        from cctv_agent.workers.tunnel_uploader import TunnelUploaderWorker
        self.upload_worker = TunnelUploaderWorker(
            self.db_manager,
            vm_url="http://34.63.62.95:8000/upload",
            buffer_minutes=10
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
        """Start a snapshot worker for each configured camera and channel."""
        config = self.config_manager.config
        # Global interval for 5 FPS
        interval = 0.2  # 5 FPS
        
        for device in config.get("devices", []):
            channels = device.get("channels", [])
            ip_address = device.get("ip")
            location_id = device.get("location_id", "default")
            org_id = config.get("org_id", "default")

            if channels:
                for channel in channels:
                    if not channel.get("enabled", True):
                        continue

                    ch_num = channel.get("channel_number", 1)
                    channel_id = f"{ip_address}_ch{ch_num:02d}"
                    
                    # Prioritize Highest Resolution (Main Stream)
                    rtsp_url = channel.get("main_stream_uri") or channel.get("sub_stream_uri") or channel.get("rtsp_url")
                    
                    worker = SnapshotWorker(
                        camera_id=channel_id,
                        location_id=location_id,
                        org_id=org_id,
                        ip_address=ip_address,
                        rtsp_url=rtsp_url,
                        interval_seconds=interval,
                        jpeg_quality=85,
                        snapshot_queue=None,
                        log_emitter=None, # In simplified mode
                        db_manager=self.db_manager,
                        camera_number=ch_num
                    )
                    worker.start()
                    self.snapshot_workers[channel_id] = worker
                    logger.info(f"Started snapshot worker for {channel_id} (5 FPS, Main Stream)")
                    
                    # Check for gaps and initiate backfill if needed
                    self._check_and_backfill(channel_id, org_id, location_id, ip_address, rtsp_url, ch_num)
                    
                    # Stagger startup to avoid overwhelming DVR
                    time.sleep(1)

    def _check_and_backfill(self, camera_id, org_id, location_id, ip_address, rtsp_url, camera_number):
        """Check for gaps and start backfill worker if significant gap found."""
        last_capture = self.db_manager.get_last_capture_time(camera_id)
        if not last_capture:
            return

        from cctv_agent.core.schedule_manager import ScheduleManager
        scheduler = ScheduleManager()
        now_utc = datetime.utcnow()
        
        # If gap > 10 minutes, try to backfill
        if now_utc - last_capture > timedelta(minutes=10):
            # Limit backfill to last 24 hours for safety
            start_backfill = max(last_capture, now_utc - timedelta(hours=24))
            
            from cctv_agent.workers.backfill_worker import BackfillWorker
            backfill = BackfillWorker(
                camera_id=camera_id,
                org_id=org_id,
                location_id=location_id,
                ip_address=ip_address,
                rtsp_base_url=rtsp_url,
                start_time=start_backfill,
                end_time=now_utc,
                db_manager=self.db_manager,
                camera_number=camera_number,
                fps=5
            )
            # We don't start it immediately to avoid congestion
            # In a real system, we'd queue these. For now, just start.
            backfill.start()

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
