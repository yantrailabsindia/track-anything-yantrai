import logging
import time
import httpx
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from PySide6.QtCore import QMutex, QWaitCondition
import cv2
import numpy as np
import base64
import os


class SnapshotWorker(QThread):
    """
    Captures frames and pushes them to the backend API.
    - Receives QImage frames from StreamWorker
    - Encodes to JPEG and saves locally
    - Sends to backend via HTTP POST
    - Maintains local folder structure: data/cctv/{username}/{YYYYMMDD}/
    """
    snapshot_sent = Signal(bool, str)  # success, message
    snapshot_saved = Signal(str)  # filename
    status_changed = Signal(str)  # status message

    def __init__(self, config_manager, user_id, api_url, token):
        super().__init__()
        self.config_manager = config_manager
        self.user_id = user_id
        self.api_url = api_url
        self.token = token  # JWT token for authentication
        self.is_running = False
        self.frame_queue = []
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()

        # Initialize data folder
        self.data_dir = Path(os.path.expanduser("~/CCTVViewer/data/cctv"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Get FPS config (default 10 FPS = 100ms interval)
        cloud = self.config_manager.get_cloud_settings()
        snapshot_config = cloud.get("snapshot", {})
        self.frame_rate_fps = snapshot_config.get("frame_rate_fps", 10)
        self.interval_ms = int(1000 / self.frame_rate_fps)

        logging.info(f"SnapshotWorker initialized: {self.frame_rate_fps} FPS ({self.interval_ms}ms interval)")

    def on_frame_captured(self, qimage, camera_id):
        """Called when StreamWorker emits a frame."""
        self.mutex.lock()
        self.frame_queue.append((qimage, camera_id, datetime.now()))
        self.mutex.unlock()
        self.wait_condition.wakeAll()

    def run(self):
        self.is_running = True
        last_push_time = {}  # Track last push time per camera

        while self.is_running:
            self.mutex.lock()
            if len(self.frame_queue) == 0:
                self.wait_condition.wait(self.mutex, 1000)  # Wait up to 1 second

            # Process one frame if available
            if len(self.frame_queue) > 0:
                frame_data = self.frame_queue.pop(0)
                self.mutex.unlock()

                qimage, camera_id, captured_at = frame_data
                current_time = time.time()

                # Check if enough time has passed for this camera (FPS limiting)
                last_time = last_push_time.get(camera_id, 0)
                time_since_last = (current_time - last_time) * 1000  # Convert to ms

                if time_since_last < self.interval_ms:
                    # Not enough time has passed, skip this frame
                    continue

                last_push_time[camera_id] = current_time

                # Convert QImage to JPEG bytes
                try:
                    # Convert QImage to numpy array
                    width = qimage.width()
                    height = qimage.height()
                    ptr = qimage.bits()
                    ptr.setsize(qimage.byteCount())
                    arr = np.array(ptr).reshape(height, width, 4)  # RGBA

                    # Convert RGBA to BGR for OpenCV
                    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

                    # Encode to JPEG
                    success, jpeg_data = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])

                    if not success:
                        logging.error(f"Failed to encode frame for {camera_id}")
                        continue

                    # Save locally
                    filename = self._save_frame_locally(camera_id, captured_at, jpeg_data)

                    if filename:
                        # Push to backend
                        self._push_frame_to_backend(camera_id, captured_at, jpeg_data)
                        self.snapshot_saved.emit(filename)

                except Exception as e:
                    logging.error(f"Error processing frame: {e}")
                    self.status_changed.emit(f"Error: {str(e)}")
            else:
                self.mutex.unlock()

    def _save_frame_locally(self, camera_id, captured_at, jpeg_data):
        """Save frame to local disk with folder structure."""
        try:
            # Create folder structure: data/cctv/{user_id}/{YYYYMMDD}/
            date_folder = captured_at.strftime("%Y%m%d")
            camera_folder = self.data_dir / self.user_id / date_folder
            camera_folder.mkdir(parents=True, exist_ok=True)

            # Generate filename: {CAMERA_ID}_{YYYYMMDD}_{HHMMSS}_{mmm}.jpg
            timestamp_str = captured_at.strftime("%Y%m%d_%H%M%S")
            milliseconds = captured_at.microsecond // 1000
            filename = f"{camera_id}_{timestamp_str}_{milliseconds:03d}.jpg"

            filepath = camera_folder / filename

            # Write JPEG data
            with open(filepath, 'wb') as f:
                f.write(jpeg_data.tobytes())

            logging.debug(f"Saved frame: {filepath}")
            return filename

        except Exception as e:
            logging.error(f"Failed to save frame locally: {e}")
            return None

    def _push_frame_to_backend(self, camera_id, captured_at, jpeg_data):
        """Send frame to backend API."""
        try:
            # Encode JPEG to base64
            b64_image = base64.b64encode(jpeg_data.tobytes()).decode('utf-8')

            payload = {
                "camera_id": camera_id,
                "captured_at": captured_at.isoformat(),
                "user_id": self.user_id,  # Send user_id instead of username
                "image_data": b64_image
            }

            headers = {
                "Authorization": f"Bearer {self.token}",  # JWT token
                "Content-Type": "application/json"
            }

            # POST to backend
            url = f"{self.api_url.rstrip('/')}/api/cctv/snapshots"

            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    self.snapshot_sent.emit(True, f"Frame {camera_id} pushed")
                    logging.debug(f"Frame pushed: {camera_id}")
                elif response.status_code == 401:
                    self.snapshot_sent.emit(False, "Authentication failed - re-login required")
                    logging.warning("Frame push failed: Authentication error")
                else:
                    self.snapshot_sent.emit(False, f"Server error: {response.status_code}")
                    logging.warning(f"Frame push failed: {response.status_code} - {response.text}")

        except Exception as e:
            self.snapshot_sent.emit(False, f"Network error: {str(e)}")
            logging.error(f"Failed to push frame: {e}")

    def set_frame_rate(self, fps):
        """Update frame rate dynamically."""
        if fps > 0:
            self.frame_rate_fps = fps
            self.interval_ms = int(1000 / fps)
            logging.info(f"Frame rate updated to {fps} FPS ({self.interval_ms}ms)")

            # Save to config
            cloud = self.config_manager.get_cloud_settings()
            if "snapshot" not in cloud:
                cloud["snapshot"] = {}
            cloud["snapshot"]["frame_rate_fps"] = fps
            self.config_manager.save_cloud_settings(cloud)

    def stop(self):
        self.is_running = False
        self.wait_condition.wakeAll()
        self.wait()
