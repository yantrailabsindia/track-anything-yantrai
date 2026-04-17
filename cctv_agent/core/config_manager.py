import json
import os
import logging
from pathlib import Path
from cctv_agent import config as agent_config

class ConfigManager:
    """
    Manages CCTV agent configuration (JSON).
    Extends base config with camera list and snapshot settings.
    """
    DEFAULT_PATH = agent_config.CONFIG_FILE

    def __init__(self, config_path=None):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_PATH
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()

    def load_config(self):
        if not self.config_path.exists():
            return self._get_default_config()
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return self._get_default_config()

    def save_config(self, config=None):
        if config:
            self.config = config
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
            return False

    def _get_default_config(self):
        return {
            "agent_id": "site-01",
            "org_id": "",
            "location_id": "",
            "api_url": "http://34.63.62.95",
            "api_key": "",
            "gcs_bucket": "",
            "gcs_path_template": "{org_id}/{location_id}/{camera_id}/{YYYY-MM-DD}/{HH}/",
            "batch_interval_seconds": 3600,  # 1 hour
            "max_local_queue_gb": 10,
            "max_retry_hours": 24,
            "default_snapshot_interval": 300,
            "default_jpeg_quality": 85,
            "default_resolution_profile": "sub",
            "cameras": []
        }

    def add_camera(self, camera_info):
        """Add or update a camera in config."""
        # Prevent duplicates by IP
        self.config["cameras"] = [
            c for c in self.config.get("cameras", [])
            if c.get("ip_address") != camera_info.get("ip_address")
        ]
        self.config["cameras"].append(camera_info)
        self.save_config()

    def get_cameras(self):
        """Get all configured cameras."""
        return self.config.get("cameras", [])

    def get_camera_by_ip(self, ip):
        """Get camera config by IP address."""
        for cam in self.get_cameras():
            if cam.get("ip_address") == ip:
                return cam
        return None

    def remove_camera(self, ip):
        """Remove camera from config."""
        self.config["cameras"] = [
            c for c in self.config.get("cameras", [])
            if c.get("ip_address") != ip
        ]
        self.save_config()

    def get_cloud_settings(self):
        """Get cloud (GCS + backend) settings."""
        return {
            "api_url": self.config.get("api_url"),
            "api_key": self.config.get("api_key"),
            "gcs_bucket": self.config.get("gcs_bucket"),
            "gcs_path_template": self.config.get("gcs_path_template"),
            "batch_interval_seconds": self.config.get("batch_interval_seconds"),
            "max_local_queue_gb": self.config.get("max_local_queue_gb"),
            "max_retry_hours": self.config.get("max_retry_hours")
        }

    def save_cloud_settings(self, settings):
        """Update cloud settings."""
        self.config.update(settings)
        self.save_config()

    def get_agent_info(self):
        """Get agent identity info."""
        return {
            "agent_id": self.config.get("agent_id"),
            "org_id": self.config.get("org_id"),
            "location_id": self.config.get("location_id")
        }

    def update_agent_info(self, agent_id=None, org_id=None, location_id=None):
        """Update agent identity."""
        if agent_id:
            self.config["agent_id"] = agent_id
        if org_id:
            self.config["org_id"] = org_id
        if location_id:
            self.config["location_id"] = location_id
        self.save_config()
