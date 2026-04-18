"""
Snapshot capture worker - one thread per camera.
Periodically grabs frames and queues for upload.
"""

import threading
import logging
import time
from datetime import datetime
from typing import Dict, Optional
from cctv_agent.services.frame_grabber import FrameGrabber
from cctv_agent.core.credential_store import CredentialStore

logger = logging.getLogger(__name__)


class SnapshotWorker:
    """Captures snapshots from a single camera on an interval."""

    def __init__(
        self,
        camera_id: str,
        location_id: str,
        org_id: str,
        ip_address: str,
        rtsp_url: str,
        interval_seconds: int,
        jpeg_quality: int,
        snapshot_queue,
        log_emitter,
        db_manager,
        camera_number: int = 1
    ):
        """
        Initialize snapshot worker.

        Args:
            camera_id: Camera ID
            location_id: Location ID
            org_id: Organization ID
            ip_address: Camera IP for credential lookup
            rtsp_url: RTSP stream URL
            interval_seconds: Capture interval in seconds
            jpeg_quality: JPEG quality (1-100)
            snapshot_queue: Queue to put snapshots on
            log_emitter: LogEmitter instance
            db_manager: DBManager instance
        """
        self.camera_id = camera_id
        self.location_id = location_id
        self.org_id = org_id
        self.ip_address = ip_address
        self.rtsp_url = rtsp_url
        self.interval_seconds = interval_seconds
        self.jpeg_quality = jpeg_quality
        self.snapshot_queue = snapshot_queue
        self.log_emitter = log_emitter
        self.db_manager = db_manager
        self.camera_number = camera_number
        self.capture_count = 0  # Sequence number for filenames

        self.stop_event = threading.Event()
        self.thread = None
        self.last_capture_time = None
        self.last_error = None

    def start(self):
        """Start the capture thread."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info(f"Started snapshot worker for camera {self.camera_id}")

    def stop(self):
        """Stop the capture thread."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            logger.info(f"Stopped snapshot worker for camera {self.camera_id}")

    def _run(self):
        """Main capture loop."""
        # Load credentials
        username, password = CredentialStore.load_credentials(self.ip_address)

        # Initialize frame grabber
        try:
            grabber = FrameGrabber(self.rtsp_url, username, password)
        except Exception as e:
            logger.error(f"Failed to initialize frame grabber for {self.camera_id}: {e}")
            self.log_emitter.emit(
                "error",
                "capture",
                f"Failed to initialize frame grabber: {e}",
                camera_id=self.camera_id
            )
            return

        next_capture = time.time()

        while not self.stop_event.is_set():
            now = time.time()

            if now >= next_capture:
                logger.info(f"Main loop: triggering capture for {self.camera_id}")
                self._capture_frame(grabber)
                next_capture = now + self.interval_seconds
                logger.info(f"Main loop: next capture in {self.interval_seconds}s")

            # Sleep briefly to avoid busy-waiting
            self.stop_event.wait(min(1.0, next_capture - time.time()))

    def _capture_frame(self, grabber: FrameGrabber):
        """Capture a single frame and queue for upload."""
        try:
            logger.debug(f"Attempting to capture frame for {self.camera_id}")
            success, jpeg_bytes = grabber.grab_frame()

            if success and jpeg_bytes:
                captured_at = datetime.utcnow()
                self.capture_count += 1
                
                # Naming: D<CAMERA NO IN 2 DIGITS>_YYYYMMDD_HHMMSS_<index>.jpg
                cam_code = f"D{self.camera_number:02d}"
                timestamp = captured_at.strftime('%Y%m%d_%H%M%S')
                filename = f"{cam_code}_{timestamp}_{self.capture_count}.jpg"
                local_file_path = f"queue/{filename}"

                # Full path for disk storage
                from cctv_agent import config as agent_config
                full_path = agent_config.QUEUE_DIR / filename
                
                # Ensure directory exists
                agent_config.QUEUE_DIR.mkdir(parents=True, exist_ok=True)
                
                # Write to disk
                with open(full_path, "wb") as f:
                    f.write(jpeg_bytes)
                
                # Add to local DB queue
                gcs_date_str = captured_at.strftime('%Y/%m/%d')
                gcs_path = f"snapshots/{self.org_id}/{self.camera_id}/{gcs_date_str}/{filename}"
                
                db_success = self.db_manager.add_snapshot_to_queue(
                    camera_id=self.camera_id,
                    location_id=self.location_id,
                    org_id=self.org_id,
                    captured_at=captured_at,
                    local_file_path=local_file_path,
                    gcs_path=gcs_path,
                    file_size_bytes=len(jpeg_bytes),
                    resolution="unknown"
                )

                if db_success:
                    self.log_emitter.emit(
                        "info",
                        "capture",
                        f"Captured and stored: {self.camera_id} ({len(jpeg_bytes)} bytes)",
                        camera_id=self.camera_id
                    )
                else:
                    logger.error(f"Failed to add snapshot to DB for {self.camera_id}")
            else:
                logger.warning(f"Snapshot capture returned no data for {self.camera_id}")
                self.last_error = "No data returned"

            self.last_capture_time = datetime.utcnow()

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error in capture frame for {self.camera_id}: {e}")
            self.log_emitter.emit(
                "error",
                "capture",
                f"Capture failed: {e}",
                camera_id=self.camera_id
            )

    def get_status(self) -> Dict:
        """Get worker status."""
        return {
            "camera_id": self.camera_id,
            "is_running": self.thread is not None and self.thread.is_alive(),
            "last_capture_time": self.last_capture_time.isoformat() if self.last_capture_time else None,
            "last_error": self.last_error
        }
