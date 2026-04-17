"""
GCS (Google Cloud Storage) integration service.
Handles direct uploads from agents and signed URL generation for downloads.
"""

import os
from datetime import timedelta
from google.cloud import storage
from google.oauth2 import service_account


class GCSService:
    def __init__(self):
        """
        Initialize GCS client.
        Requires environment variables:
        - GCS_PROJECT_ID
        - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)
        - Or use Application Default Credentials (gcloud auth application-default login)
        """
        self.project_id = os.getenv("GCS_PROJECT_ID")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")

        if not self.project_id or not self.bucket_name:
            raise ValueError(
                "GCS_PROJECT_ID and GCS_BUCKET_NAME environment variables must be set"
            )

        # Try to use GOOGLE_APPLICATION_CREDENTIALS, fall back to default credentials
        try:
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.client = storage.Client(
                    project=self.project_id,
                    credentials=credentials
                )
            else:
                # Use Application Default Credentials
                self.client = storage.Client(project=self.project_id)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GCS client: {e}")

        self.bucket = self.client.bucket(self.bucket_name)

    def generate_signed_upload_url(
        self,
        object_path: str,
        expiry_minutes: int = 15
    ) -> str:
        """
        Generate a signed URL for direct upload from CCTV agent.

        Args:
            object_path: Full GCS path (e.g., "org-id/location-id/camera-id/2026-04-13/14/snapshot_1234.jpg")
            expiry_minutes: URL expiry time in minutes (default 15)

        Returns:
            Signed upload URL
        """
        blob = self.bucket.blob(object_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiry_minutes),
            method="PUT",
            content_type="image/jpeg"
        )

        return url

    def generate_signed_download_url(
        self,
        object_path: str,
        expiry_hours: int = 1
    ) -> str:
        """
        Generate a signed URL for downloading a snapshot.

        Args:
            object_path: Full GCS path
            expiry_hours: URL expiry time in hours (default 1)

        Returns:
            Signed download URL
        """
        blob = self.bucket.blob(object_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiry_hours),
            method="GET"
        )

        return url

    def upload_blob(
        self,
        object_path: str,
        data_bytes: bytes,
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload data directly to GCS (server-side upload).

        Args:
            object_path: Full GCS path
            data_bytes: File content
            content_type: MIME type

        Returns:
            GCS object path
        """
        blob = self.bucket.blob(object_path)
        blob.upload_from_string(data_bytes, content_type=content_type)
        return object_path

    def delete_blob(self, object_path: str) -> None:
        """Delete an object from GCS."""
        blob = self.bucket.blob(object_path)
        blob.delete()

    def blob_exists(self, object_path: str) -> bool:
        """Check if an object exists in GCS."""
        blob = self.bucket.blob(object_path)
        return blob.exists()

    def get_blob_metadata(self, object_path: str) -> dict:
        """Get metadata for a blob (size, updated time, etc.)."""
        blob = self.bucket.blob(object_path)
        blob.reload()
        return {
            "name": blob.name,
            "size": blob.size,
            "content_type": blob.content_type,
            "updated": blob.updated,
            "time_created": blob.time_created
        }


# Singleton instance
_gcs_service = None


def get_gcs_service() -> GCSService:
    """Get or create GCS service singleton."""
    global _gcs_service
    if _gcs_service is None:
        _gcs_service = GCSService()
    return _gcs_service
