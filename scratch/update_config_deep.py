import json
from pathlib import Path

def update_config():
    config_path = Path.home() / "CCTVAgent" / "config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # New verified URL
        new_url = "rtsp://admin:mohit123@192.168.1.12:5543/live/channel0"
        target_ip = "192.168.1.12"
        
        # Update devices (handles both 'ip' and 'ip_address')
        for device in config.get("devices", []):
            if device.get("ip") == target_ip or device.get("ip_address") == target_ip:
                device["rtsp_url"] = new_url
                device["snapshot_interval_seconds"] = 5
                # Also update channels if they exist
                for channel in device.get("channels", []):
                    channel["sub_stream_uri"] = new_url
        
        # Update active_streams in cloud settings
        cloud = config.get("cloud", {})
        for stream in cloud.get("active_streams", []):
            # handles both string keys and dict objects if applicable
            if isinstance(stream, dict) and (stream.get("ip") == target_ip or stream.get("ip_address") == target_ip):
                stream["rtsp_url"] = new_url
        
        # Also handle the string list format if that's what's used
        # In cloud['active_streams'], sometimes it's just "ip:port"
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        print(f"Deep-updated config.json with verified RTSP URL: {new_url}")
        return True
    return False

if __name__ == "__main__":
    update_config()
