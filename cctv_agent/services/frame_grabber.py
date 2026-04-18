"""
Single-frame grabber from RTSP streams using OpenCV.
Includes a threaded watchdog to prevent indefinite blocking.
"""

import threading
import cv2
import logging
import time
import queue
import os
from typing import Tuple, Optional

# Force TCP for all RTSP captures to improve reliability over congested networks
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

logger = logging.getLogger(__name__)


class FrameGrabber:
    """
    Grab a single frame from an RTSP stream.
    Includes a watchdog mechanism to prevent hanging on unresponsive cameras.
    """

    def __init__(self, rtsp_url: str, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize frame grabber with credentials and watchdog state.
        """
        self.rtsp_url = self._inject_credentials(rtsp_url, username, password)
        self.capture_thread = None
        self._lock = threading.Lock()

    def _inject_credentials(self, url: str, username: Optional[str], password: Optional[str]) -> str:
        """Inject credentials into RTSP URL if not already present."""
        if not username or not password:
            return url

        # Check if credentials already in URL
        if "@" in url and url.startswith("rtsp://"):
            return url

        # Inject: rtsp://user:pass@host/...
        if url.startswith("rtsp://"):
            url = url.replace("rtsp://", f"rtsp://{username}:{password}@")
        elif url.startswith("rtsp+tcp://"):
            url = url.replace("rtsp+tcp://", f"rtsp+tcp://{username}:{password}@")

        return url

    def grab_frame(self, timeout: int = 15) -> Tuple[bool, Optional[bytes]]:
        """
        Grab a single frame using a separate thread with a hard watchdog.
        Returns (success, jpeg_bytes).
        """
        # Thread safety: ensure only one thread is trying to capture at a time
        with self._lock:
            if self.capture_thread and self.capture_thread.is_alive():
                logger.warning(f"Previous capture thread for {self.rtsp_url[:50]} is still running. Skipping this attempt.")
                return False, None
            
            logger.info(f"Initiating capture from {self.rtsp_url[:50]}...")
            result_queue = queue.Queue()

            def _target():
                cap = None
                try:
                    # VideoCapture can block indefinitely in some environments
                    cap = cv2.VideoCapture(self.rtsp_url)
                    if not cap.isOpened():
                        logger.warning(f"Failed to open source: {self.rtsp_url[:50]}")
                        result_queue.put((False, None))
                        return
                    
                    if hasattr(cv2, 'CAP_PROP_BUFFERSIZE'):
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        success, jpeg_bytes = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        if success:
                            result_queue.put((True, jpeg_bytes.tobytes()))
                            return
                except Exception as e:
                    logger.error(f"Threaded capture exception: {e}")
                    result_queue.put((False, None))
                finally:
                    if cap:
                        cap.release()

            self.capture_thread = threading.Thread(target=_target, daemon=True)
            self.capture_thread.start()
        
        try:
            # Wait for thread with hard timeout
            success, data = result_queue.get(timeout=timeout)
            if success:
                logger.info("Successfully captured frame.")
            return success, data
        except queue.Empty:
            logger.warning(f"Capture TIMEOUT (> {timeout}s) for {self.rtsp_url[:50]}")
            return False, None
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
            return False, None


class PersistentFrameGrabber:
    """
    Maintains a persistent RTSP connection and continuously reads frames.
    Optimized for high-frequency capture (e.g., 5-30 FPS).
    """

    def __init__(self, rtsp_url: str, username: Optional[str] = None, password: Optional[str] = None):
        self.rtsp_url = self._inject_credentials(rtsp_url, username, password)
        self.cap = None
        self.last_frame = None
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
        self.last_capture_time = 0
        self.error_count = 0

    def _inject_credentials(self, url: str, username: Optional[str], password: Optional[str]) -> str:
        if not username or not password or "@" in url:
            return url
        if url.startswith("rtsp://"):
            return url.replace("rtsp://", f"rtsp://{username}:{password}@")
        return url

    def start(self):
        """Start the background capture thread."""
        with self._lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.thread.start()
                logger.info(f"Persistent grabber started for {self.rtsp_url[:50]}")

    def stop(self):
        """Stop the background capture thread."""
        with self._lock:
            self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None

    def _capture_loop(self):
        """Background thread that continuously reads from the stream."""
        while self.running:
            try:
                if self.cap is None or not self.cap.isOpened():
                    logger.info(f"Opening persistent stream: {self.rtsp_url[:50]}")
                    self.cap = cv2.VideoCapture(self.rtsp_url)
                    if not self.cap.isOpened():
                        logger.warning(f"Failed to open persistent stream, retrying in 5s...")
                        time.sleep(5)
                        continue
                    
                    if hasattr(cv2, 'CAP_PROP_BUFFERSIZE'):
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self._lock:
                        self.last_frame = frame.copy()
                        self.last_capture_time = time.time()
                    self.error_count = 0
                else:
                    self.error_count += 1
                    if self.error_count > 30: # ~1 second of failure
                        logger.warning("Persistent stream lost connection, reconnecting...")
                        self.cap.release()
                        self.cap = None
                        time.sleep(1)
            except Exception as e:
                logger.error(f"Error in persistent capture loop: {e}")
                time.sleep(1)
            
            # Tiny sleep to prevent 100% CPU on one core if cap.read() is non-blocking
            time.sleep(0.001)

    def get_frame(self) -> Tuple[bool, Optional[bytes]]:
        """Get the latest encoded frame."""
        with self._lock:
            if self.last_frame is None:
                return False, None
            
            try:
                # Only encode when requested to save CPU in background loop
                success, jpeg_bytes = cv2.imencode('.jpg', self.last_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if success:
                    return True, jpeg_bytes.tobytes()
            except Exception as e:
                logger.error(f"Failed to encode frame: {e}")
            
            return False, None
