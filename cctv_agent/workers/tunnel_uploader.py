"""
Service 2 & 3: Tunnel Uploader and Cleanup.
Moves ripe snapshots (10+ mins old) to the remote VM and deletes local files.
"""

import threading
import logging
import time
import os
import httpx
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from cctv_agent import config as agent_config
from cctv_agent.services.db_manager import DBManager

logger = logging.getLogger(__name__)

class TunnelUploaderWorker:
    """
    Background worker that moves local frames to a remote VM after a 10-minute buffer.
    Service 2: Uploader
    Service 3: Cleanup
    """

    def __init__(self, db_manager: DBManager, vm_url: str = "http://34.63.62.95:8000/upload", buffer_minutes: int = 10):
        self.db_manager = db_manager
        self.vm_url = vm_url
        self.buffer_minutes = buffer_minutes
        self.stop_event = threading.Event()
        self.thread = None
        self.max_workers = 10 # High concurrency to handle 80 FPS flow

    def start(self):
        """Start the uploader thread."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.info(f"Service 2 & 3: Tunnel Uploader started (VM: {self.vm_url}, Buffer: {self.buffer_minutes}m)")

    def stop(self):
        """Stop the uploader thread."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("Service 2 & 3: Tunnel Uploader stopped")

    def _run_loop(self):
        """Main loop to process ripe snapshots."""
        while not self.stop_event.is_set():
            try:
                # Fetch snapshots that have passed the 10-minute buffer
                ripe_snapshots = self.db_manager.get_ripe_snapshots(buffer_minutes=self.buffer_minutes, limit=200)

                if not ripe_snapshots:
                    # Nothing ripe yet, wait a bit
                    self.stop_event.wait(10)
                    continue

                logger.info(f"Processing {len(ripe_snapshots)} ripe snapshots for tunnel upload...")
                
                # Process in parallel to keep up with the 5 FPS x 16 camera rate
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    executor.map(self._process_single_snapshot, ripe_snapshots)

                # Short sleep to prevent CPU hammering if many records are ripe
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in Tunnel Uploader loop: {e}")
                self.stop_event.wait(5)

    def _process_single_snapshot(self, snapshot: dict):
        """Upload a single file and cleanup on success."""
        snapshot_id = snapshot["id"]
        camera_id = snapshot["camera_id"]
        local_path = snapshot["local_file_path"]
        captured_at = snapshot["captured_at"]
        org_id = snapshot.get("org_id", "default")

        # Resolve full path
        filename = local_path.replace("queue/", "")
        full_path = agent_config.QUEUE_DIR / filename

        if not full_path.exists():
            logger.warning(f"File missing for ripe snapshot {snapshot_id}: {full_path}. Marking as uploaded.")
            self.db_manager.mark_uploaded(snapshot_id)
            return

        try:
            # Service 2: Tunnelling to VM
            with open(full_path, "rb") as f:
                files = {"file": (filename, f, "image/jpeg")}
                data = {
                    "camera_id": camera_id,
                    "captured_at": captured_at,
                    "filename": filename,
                    "org_id": org_id
                }
                
                # Use a larger timeout for potential network jitter
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(self.vm_url, data=data, files=files)
                
                if response.status_code == 200:
                    # Service 3: Transactional Cleanup
                    # logger.debug(f"Successfully tunnelled {filename} to VM.")
                    self.db_manager.cleanup_local_file_after_upload(snapshot_id, local_path)
                else:
                    logger.error(f"VM upload failed for {filename}: HTTP {response.status_code} - {response.text}")
                    # Increment retry count in DB or just leave for next loop
                    new_retry = snapshot.get("retry_count", 0) + 1
                    self.db_manager.mark_failed(snapshot_id, f"VM HTTP {response.status_code}", new_retry)

        except Exception as e:
            logger.error(f"Failed to tunnel snapshot {snapshot_id}: {e}")
            new_retry = snapshot.get("retry_count", 0) + 1
            self.db_manager.mark_failed(snapshot_id, str(e), new_retry)
