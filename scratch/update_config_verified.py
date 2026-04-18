import json
from pathlib import Path

def update_config():
    config_path = Path.home() / "CCTVAgent" / "config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # New verified URL
        new_url = "rtsp://admin:mohit123@192.168.1.12:5543/live/channel0"
        
        # Update devices
        for device in config.get("devices", []):
            if device.get("ip_address") == "192.168.1.12":
                device["rtsp_url"] = new_url
                for channel in device.get("channels", []):
                    channel["sub_stream_uri"] = new_url
        
        # Update active_streams
        for stream in config.get("cloud", {}).get("active_streams", []):
            if stream.get("ip") == "192.168.1.12":
                stream["rtsp_url"] = new_url
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        print(f"Updated config.json with verified RTSP URL: {new_url}")
        return True
    return False

if __name__ == "__main__":
    update_config()
