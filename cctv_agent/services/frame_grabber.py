"""
Single-frame grabber from RTSP streams using OpenCV.
Includes a threaded watchdog to prevent indefinite blocking.
"""

import threading
import cv2
import logging
import time
import queue
from typing import Tuple, Optional

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
                    
                    logger.info(f"Capture read failed for {self.rtsp_url[:50]}")
                    result_queue.put((False, None))
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
