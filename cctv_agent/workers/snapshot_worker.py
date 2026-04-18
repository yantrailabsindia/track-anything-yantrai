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

        # Initialize schedule manager
        from cctv_agent.core.schedule_manager import ScheduleManager
        scheduler = ScheduleManager(start_hour=9, end_hour=22)

        # Initialize persistent frame grabber
        try:
            from cctv_agent.services.frame_grabber import PersistentFrameGrabber
            grabber = PersistentFrameGrabber(self.rtsp_url, username, password)
            grabber.start()
        except Exception as e:
            logger.error(f"Failed to initialize persistent grabber for {self.camera_id}: {e}")
            return

        try:
            while not self.stop_event.is_set():
                # Check schedule
                if not scheduler.is_currently_active():
                    # Outside 9am-10pm IST, sleep longer
                    self.stop_event.wait(60)
                    continue

                now = time.time()
                
                # Capture frame
                self._capture_frame_persistent(grabber, scheduler)

                # Wait for next frame (5 FPS = 0.2s interval)
                # account for processing time
                elapsed = time.time() - now
                wait_time = max(0.01, self.interval_seconds - elapsed)
                self.stop_event.wait(wait_time)
        finally:
            grabber.stop()

    def _capture_frame_persistent(self, grabber, scheduler):
        """Capture a frame from the persistent grabber."""
        success, jpeg_bytes = grabber.get_frame()
        if success and jpeg_bytes:
            self._process_frame(jpeg_bytes, scheduler)
        else:
            # Maybe stream is reconnecting
            pass

    def _process_frame(self, jpeg_bytes, scheduler):
        """Save frame to disk and add to DB."""
        captured_at = scheduler.get_ist_now()
        self.capture_count += 1
        
        # Naming: D<CAMERA NO>_YYYYMMDD_HHMMSSMMM.jpg
        cam_code = f"D{self.camera_number:02d}"
        # %f gives microseconds, we take first 3 for milliseconds
        timestamp = captured_at.strftime('%Y%m%d_%H%M%S%f')[:-3]
        filename = f"{cam_code}_{timestamp}.jpg"
        
        from cctv_agent import config as agent_config
        full_path = agent_config.QUEUE_DIR / filename
        
        # Write to disk
        try:
            with open(full_path, "wb") as f:
                f.write(jpeg_bytes)
            
            # Add to local DB queue (minimal metadata for speed)
            gcs_date_str = captured_at.strftime('%Y/%m/%d')
            gcs_path = f"snapshots/{self.org_id}/{self.camera_id}/{gcs_date_str}/{filename}"
            
            self.db_manager.add_snapshot_to_queue(
                camera_id=self.camera_id,
                location_id=self.location_id,
                org_id=self.org_id,
                captured_at=captured_at,
                local_file_path=f"queue/{filename}",
                gcs_path=gcs_path,
                file_size_bytes=len(jpeg_bytes),
                resolution="high-res"
            )
            self.last_capture_time = captured_at
        except Exception as e:
            logger.error(f"Failed to process frame for {self.camera_id}: {e}")

    def _capture_frame(self, grabber: FrameGrabber):
        # Kept for backward compatibility if needed, but not used in 5FPS mode
        pass

    def get_status(self) -> Dict:
        """Get worker status."""
        return {
            "camera_id": self.camera_id,
            "is_running": self.thread is not None and self.thread.is_alive(),
            "last_capture_time": self.last_capture_time.isoformat() if self.last_capture_time else None,
            "last_error": self.last_error
        }
