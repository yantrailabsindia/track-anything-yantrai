import json
from pathlib import Path

def update_rtsp_url():
    config_path = Path.home() / "CCTVAgent" / "config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # New CP PLUS URL
        new_url = "rtsp://admin:mohit123@192.168.1.12:554/cam/realmonitor?channel=1&subtype=1"
        
        # Update devices
        for device in config.get("devices", []):
            if device.get("ip") == "192.168.1.12":
                for channel in device.get("channels", []):
                    channel["sub_stream_uri"] = new_url
        
        # Update active_streams
        for stream in config.get("cloud", {}).get("active_streams", []):
            if stream.get("ip") == "192.168.1.12":
                stream["rtsp_url"] = new_url
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        print(f"Updated config.json with new RTSP URL: {new_url}")
        return True
    return False

if __name__ == "__main__":
    update_rtsp_url()
