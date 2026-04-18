import asyncio
import sys
from pathlib import Path

# Add cctv_agent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cctv_agent.core.onvif_client import ONVIFClient

def probe_camera():
    ip = "192.168.1.12"
    user = "admin"
    password = "mohit123"
    port = 8000
    
    print(f"Probing ONVIF for {ip}:{port}...")
    client = ONVIFClient(ip, user, password, port=port)
    
    try:
        if client.connect():
            print("Connected to ONVIF!")
            channels = client.get_channels()
            print(f"Found {len(channels)} channels:")
            for ch in channels:
                print(f"  - Channel {ch['channel_number']}: {ch['name']} (Token: {ch['token']})")
                print(f"    Sub Stream URI: {ch['sub_stream_uri']}")
        else:
            print("Failed to connect to ONVIF.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe_camera()
