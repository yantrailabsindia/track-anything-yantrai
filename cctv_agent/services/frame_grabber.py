"""
Single-frame grabber from RTSP streams using OpenCV.
Adapted from stream_worker.py with exponential backoff retry.
"""

import cv2
import logging
import time
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class FrameGrabber:
    """
    Grab a single frame from an RTSP stream.
    Includes exponential backoff retry logic.
    """

    def __init__(self, rtsp_url: str, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize frame grabber with credentials if needed.

        Args:
            rtsp_url: RTSP URL (with or without auth)
            username: Optional username for RTSP authentication
            password: Optional password for RTSP authentication
        """
        self.rtsp_url = self._inject_credentials(rtsp_url, username, password)
        self.initial_backoff = 2
        self.max_backoff = 30
        self.max_retry_attempts = 5

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

    def grab_frame(self, timeout: int = 10) -> Tuple[bool, Optional[bytes]]:
        """
        Grab a single frame from the RTSP stream and encode as JPEG.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            Tuple of (success: bool, jpeg_bytes: Optional[bytes])
        """
        backoff = self.initial_backoff

        for attempt in range(self.max_retry_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retry_attempts} to grab frame from {self.rtsp_url[:50]}...")

                # Open capture
                cap = cv2.VideoCapture(self.rtsp_url)
                cap.set(cv2.CAP_PROP_CONNECT_TIMEOUT, int(timeout * 1000))

                # Try to grab frame
                ret, frame = cap.read()
                cap.release()

                if ret and frame is not None and frame.size > 0:
                    # Encode to JPEG
                    success, jpeg_bytes = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if success:
                        logger.debug(f"Successfully grabbed frame ({len(jpeg_bytes)} bytes)")
                        return True, jpeg_bytes.tobytes()
                    else:
                        logger.warning("Failed to encode frame to JPEG")
                else:
                    logger.warning(f"Failed to read frame (ret={ret}, frame={frame is not None})")

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

            # Exponential backoff before retry
            if attempt < self.max_retry_attempts - 1:
                logger.debug(f"Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff)

        logger.error(f"Failed to grab frame after {self.max_retry_attempts} attempts")
        return False, None
