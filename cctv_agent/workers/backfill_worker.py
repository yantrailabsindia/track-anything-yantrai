"""
Backfill worker - handles gap recovery from DVR hard disk using RTSP playback.
Runs one camera at a time to prevent system overload.
"""

import threading
import logging
import time
from datetime import datetime, timedelta
import cv2
from cctv_agent.core.credential_store import CredentialStore

logger = logging.getLogger(__name__)


class BackfillWorker:
    """Recovers missing frames from DVR using playback RTSP streams."""

    def __init__(
        self,
        camera_id: str,
        org_id: str,
        location_id: str,
        ip_address: str,
        rtsp_base_url: str,
        start_time: datetime,
        end_time: datetime,
        db_manager,
        camera_number: int,
        fps: int = 5
    ):
        self.camera_id = camera_id
        self.org_id = org_id
        self.location_id = location_id
        self.ip_address = ip_address
        self.db_manager = db_manager
        self.camera_number = camera_number
        self.target_fps = fps
        self.frame_interval = 1.0 / fps
        
        # Format playback URL
        # rtsp://user:pass@ip:554/Streaming/tracks/101/?starttime=20240418T100000Z&endtime=20240418T110000Z
        username, password = CredentialStore.load_credentials(self.ip_address)
        
        # Clean the base URL (e.g. rtsp://.../Streaming/Channels/101 -> .../Streaming/tracks/101)
        # Note: Hikvision tracks usually match channel number*100 + 1
        track_id = f"{self.camera_number:d}01"
        self.playback_url = f"rtsp://{username}:{password}@{self.ip_address}:554/Streaming/tracks/{track_id}/?"
        self.playback_url += f"starttime={start_time.strftime('%Y%m%dT%H%M%SZ')}&"
        self.playback_url += f"endtime={end_time.strftime('%Y%m%dT%H%M%SZ')}"
        
        self.current_time = start_time
        self.end_time = end_time
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"Backfill started for {self.camera_id} from {self.current_time} to {self.end_time}")

    def _run(self):
        cap = cv2.VideoCapture(self.playback_url)
        if not cap.isOpened():
            logger.error(f"Failed to open playback stream for {self.camera_id}")
            return

        capture_count = 0
        try:
            while not self.stop_event.is_set() and self.current_time < self.end_time:
                ret, frame = cap.read()
                if not ret:
                    break

                # Process the frame
                success, jpeg_bytes = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if success:
                    self._save_recovered_frame(jpeg_bytes, self.current_time)
                    capture_count += 1

                # Advance current time (simulated)
                self.current_time += timedelta(seconds=self.frame_interval)
                
                # Controlled capture speed (e.g. 10x real-time)
                # We don't wait for actual 0.2s, we want to finish fast
                time.sleep(0.01) 

            logger.info(f"Backfill completed for {self.camera_id}. Recovered {capture_count} frames.")
        finally:
            cap.release()

    def _save_recovered_frame(self, jpeg_bytes, timestamp):
        """Save a recovered frame with its original timestamp."""
        cam_code = f"D{self.camera_number:02d}"
        time_str = timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{cam_code}_{time_str}_recovered.jpg"
        
        from cctv_agent import config as agent_config
        full_path = agent_config.QUEUE_DIR / filename
        
        try:
            with open(full_path, "wb") as f:
                f.write(jpeg_bytes)
            
            gcs_date_str = timestamp.strftime('%Y/%m/%d')
            gcs_path = f"snapshots/{self.org_id}/{self.camera_id}/{gcs_date_str}/{filename}"
            
            self.db_manager.add_snapshot_to_queue(
                camera_id=self.camera_id,
                location_id=self.location_id,
                org_id=self.org_id,
                captured_at=timestamp,
                local_file_path=f"queue/{filename}",
                gcs_path=gcs_path,
                file_size_bytes=len(jpeg_bytes),
                resolution="recovered"
            )
        except Exception as e:
            logger.error(f"Failed to save recovered frame: {e}")
