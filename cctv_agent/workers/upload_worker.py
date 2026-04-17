"""
Upload worker - handles hourly batch upload to GCS + backend.
Also responds to manual upload signals (FORCE_UPLOAD file).
"""

import threading
import logging
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import httpx
import json

from cctv_agent import config as agent_config
from cctv_agent.services.gcs_uploader import GCSUploader
from cctv_agent.services.db_manager import DBManager

logger = logging.getLogger(__name__)


class UploadWorker:
    """Handles periodic and on-demand snapshot uploads to GCS + backend."""

    def __init__(
        self,
        config_manager,
        db_manager: DBManager,
        log_emitter,
        gcs_uploader: Optional[GCSUploader] = None
    ):
        """
        Initialize upload worker.

        Args:
            config_manager: ConfigManager instance
            db_manager: DBManager instance
            log_emitter: LogEmitter instance
            gcs_uploader: GCSUploader instance (optional, lazy-load)
        """
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.log_emitter = log_emitter
        self.gcs_uploader = gcs_uploader

        self.stop_event = threading.Event()
        self.thread = None
        self.last_upload_time = None

    def start(self):
        """Start the upload worker thread."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("Started upload worker")

    def stop(self):
        """Stop the upload worker thread."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            logger.info("Stopped upload worker")

    def _run(self):
        """Main upload loop."""
        batch_interval = self.config_manager.config.get("batch_interval_seconds", 3600)
        next_upload = time.time()

        while not self.stop_event.is_set():
            now = time.time()
            force_upload = agent_config.FORCE_UPLOAD_FILE.exists()

            if force_upload or now >= next_upload:
                self._do_upload()
                next_upload = now + batch_interval

                # Clean up force upload signal
                if force_upload:
                    try:
                        agent_config.FORCE_UPLOAD_FILE.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to delete FORCE_UPLOAD signal: {e}")

            # Sleep
            self.stop_event.wait(min(1.0, next_upload - time.time()))

    def _do_upload(self):
        """Execute batch upload."""
        try:
            logger.info("Starting batch upload...")
            self.log_emitter.emit("info", "upload", "Starting batch upload")

            # Get pending snapshots
            pending = self.db_manager.get_pending_snapshots(limit=100)

            if not pending:
                logger.debug("No pending snapshots to upload")
                return

            logger.info(f"Uploading {len(pending)} snapshots...")
            self.log_emitter.emit("info", "upload", f"Uploading {len(pending)} snapshots")

            # Ensure GCS uploader initialized
            if not self.gcs_uploader:
                cloud_settings = self.config_manager.get_cloud_settings()
                self.gcs_uploader = GCSUploader(
                    bucket_name=cloud_settings.get("gcs_bucket"),
                    project_id=cloud_settings.get("gcs_project") or None
                )

            # Upload each snapshot
            success_count = 0
            for snapshot in pending:
                if self._upload_snapshot(snapshot):
                    success_count += 1
                    self.db_manager.mark_uploaded(snapshot["id"])

            self.log_emitter.emit(
                "info",
                "upload",
                f"Batch uploaded: {success_count}/{len(pending)} success",
            )

            self.last_upload_time = datetime.utcnow()
            self.db_manager.set_status("last_upload_at", self.last_upload_time.isoformat())

            logger.info(f"Batch upload complete: {success_count}/{len(pending)} success")

        except Exception as e:
            logger.error(f"Batch upload failed: {e}")
            self.log_emitter.emit("error", "upload", f"Batch upload failed: {e}")

    def _upload_snapshot(self, snapshot: dict) -> bool:
        """Upload a single snapshot to GCS and report metadata."""
        camera_id = snapshot["camera_id"]
        local_file_path = snapshot["local_file_path"]
        gcs_path = snapshot["gcs_path"]
        file_size = snapshot["file_size_bytes"]

        try:
            # Read JPEG from disk
            full_path = agent_config.QUEUE_DIR / local_file_path.replace("queue/", "")
            if not full_path.exists():
                logger.warning(f"Snapshot file not found: {full_path}")
                return False

            with open(full_path, "rb") as f:
                jpeg_bytes = f.read()

            # Upload to GCS
            if not self.gcs_uploader.upload_snapshot(gcs_path, jpeg_bytes):
                logger.warning(f"GCS upload failed for {gcs_path}")
                return False

            logger.debug(f"Uploaded to GCS: {gcs_path}")

            # Report metadata to backend
            if not self._report_metadata(snapshot):
                logger.warning(f"Backend metadata report failed for {camera_id}")
                # Continue anyway - GCS has the file
                return True

            # Delete local file
            try:
                full_path.unlink()
                logger.debug(f"Deleted local file: {full_path}")
            except Exception as e:
                logger.warning(f"Failed to delete local file {full_path}: {e}")

            return True

        except Exception as e:
            logger.error(f"Snapshot upload failed for {camera_id}: {e}")
            return False

    def _report_metadata(self, snapshot: dict) -> bool:
        """Report snapshot metadata to backend."""
        try:
            config = self.config_manager.config
            api_url = config.get("api_url", "http://localhost:8765")
            api_key = config.get("api_key", "")

            if not api_key:
                logger.warning("No API key configured, skipping metadata report")
                return False

            payload = {
                "camera_id": snapshot["camera_id"],
                "captured_at": snapshot["captured_at"].isoformat(),
                "gcs_path": snapshot["gcs_path"],
                "file_size_bytes": snapshot["file_size_bytes"],
                "resolution": snapshot.get("resolution")
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{api_url}/api/cctv/snapshots",
                    json=payload,
                    params={"api_key": api_key}
                )
                response.raise_for_status()

            logger.debug(f"Reported metadata for snapshot {snapshot['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to report metadata: {e}")
            return False

    def get_status(self) -> dict:
        """Get upload worker status."""
        stats = self.db_manager.get_queue_stats()
        return {
            "is_running": self.thread is not None and self.thread.is_alive(),
            "last_upload_time": self.last_upload_time.isoformat() if self.last_upload_time else None,
            **stats
        }
