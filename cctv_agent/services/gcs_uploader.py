"""
Google Cloud Storage uploader for CCTV snapshots.
Wraps google-cloud-storage SDK.
"""

import logging
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account
import os

logger = logging.getLogger(__name__)


class GCSUploader:
    """
    Handles direct upload of snapshots to Google Cloud Storage.
    """

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize GCS uploader.

        Args:
            bucket_name: GCS bucket name (e.g., "my-bucket")
            project_id: GCP project ID (optional, uses default if not provided)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id or os.getenv("GCS_PROJECT_ID")

        try:
            # Try to use GOOGLE_APPLICATION_CREDENTIALS, fall back to default
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.client = storage.Client(
                    project=self.project_id,
                    credentials=credentials
                )
                logger.info(f"GCS client initialized with service account from {credentials_path}")
            else:
                # Use Application Default Credentials
                self.client = storage.Client(project=self.project_id)
                logger.info("GCS client initialized with Application Default Credentials")

            self.bucket = self.client.bucket(self.bucket_name)

        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise

    def upload_snapshot(
        self,
        object_path: str,
        jpeg_bytes: bytes,
        content_type: str = "image/jpeg"
    ) -> bool:
        """
        Upload JPEG snapshot to GCS.

        Args:
            object_path: Full GCS path (e.g., "org-id/location-id/camera-id/2026-04-13/14/snapshot_1234.jpg")
            jpeg_bytes: JPEG image data
            content_type: MIME type (default image/jpeg)

        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(object_path)
            blob.upload_from_string(jpeg_bytes, content_type=content_type)
            logger.debug(f"Uploaded snapshot: {object_path} ({len(jpeg_bytes)} bytes)")
            return True

        except Exception as e:
            logger.error(f"Failed to upload snapshot to {object_path}: {e}")
            return False

    def blob_exists(self, object_path: str) -> bool:
        """Check if a blob exists in GCS."""
        try:
            blob = self.bucket.blob(object_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Failed to check blob existence for {object_path}: {e}")
            return False

    def delete_blob(self, object_path: str) -> bool:
        """Delete a blob from GCS."""
        try:
            blob = self.bucket.blob(object_path)
            blob.delete()
            logger.debug(f"Deleted blob: {object_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete blob {object_path}: {e}")
            return False

    def get_blob_size(self, object_path: str) -> Optional[int]:
        """Get size of a blob in bytes."""
        try:
            blob = self.bucket.blob(object_path)
            blob.reload()
            return blob.size
        except Exception as e:
            logger.error(f"Failed to get blob size for {object_path}: {e}")
            return None

    def health_check(self) -> bool:
        """Check if bucket is accessible."""
        try:
            # Try to list one object
            list(self.bucket.list_blobs(max_results=1))
            logger.debug("GCS health check passed")
            return True
        except Exception as e:
            logger.error(f"GCS health check failed: {e}")
            return False
