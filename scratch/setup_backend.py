import httpx
import json

def setup_backend_data():
    org_id = "724bd06a-d244-46af-a716-60def5d1c022"
    
    try:
        # 1. Create Location
        loc_res = httpx.post(
            f"http://localhost:8765/api/cctv/locations?org_id={org_id}",
            json={
                "name": "Office",
                "timezone": "IST"
            }
        )
        if loc_res.status_code == 200:
            location_id = loc_res.json()["id"]
            print(f"Location created: {location_id}")
        else:
            print(f"Location creation failed: {loc_res.status_code} - {loc_res.text}")
            # Try to get existing locations
            list_res = httpx.get(f"http://localhost:8765/api/cctv/locations?org_id={org_id}")
            if list_res.status_code == 200 and list_res.json():
                location_id = list_res.json()[0]["id"]
                print(f"Using existing location: {location_id}")
            else:
                return

        # 2. Create Camera
        cam_res = httpx.post(
            f"http://localhost:8765/api/cctv/cameras?org_id={org_id}",
            json={
                "location_id": location_id,
                "name": "Front Door",
                "ip_address": "192.168.1.12",
                "rtsp_url": "rtsp://admin:mohit123@192.168.1.12:554/live/channel0",
                "snapshot_interval_seconds": 30
            }
        )
        if cam_res.status_code == 200:
            camera_id = cam_res.json()["id"]
            print(f"Camera created: {camera_id}")
            
            # Update config.json to use the correct camera ID
            from pathlib import Path
            config_path = Path.home() / "CCTVAgent" / "config.json"
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # The agent uses the id from active_streams or devices
            config["cloud"]["active_streams"][0]["id"] = camera_id
            config["devices"][0]["id"] = camera_id
            config["devices"][0]["location_id"] = location_id
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            print("Updated config.json with correct Camera ID and Location ID")
            
        else:
            print(f"Camera creation failed: {cam_res.status_code} - {cam_res.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_backend_data()
