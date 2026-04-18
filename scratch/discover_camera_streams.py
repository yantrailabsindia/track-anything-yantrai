import sys
from pathlib import Path

# Add cctv_agent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cctv_agent.core.onvif_client import ONVIFClient

def main():
    ip = "192.168.1.12"
    user = "admin"
    password = "mohit123"
    port = 8000
    
    print(f"Connecting to ONVIF at {ip}:{port}...")
    client = ONVIFClient(ip, user, password, port=port)
    
    if client.connect():
        print("Connected! Fetching device info...")
        info = client.get_device_info()
        if info:
            print(f"Device: {info}")
            
        print("\nFetching Media Profiles and Stream URIs...")
        channels = client.get_channels()
        if not channels:
            print("No media profiles found.")
            return
            
        print(f"Found {len(channels)} profiles:")
        for ch in channels:
            print(f"\n--- Channel {ch['channel_number']}: {ch['name']} ---")
            print(f"  Token: {ch['token']}")
            print(f"  Stream URI: {ch['sub_stream_uri']}")
            print(f"  Resolution: {ch['resolution']}")
            
        # Select the first available stream
        if channels:
            best_uri = channels[0]['sub_stream_uri']
            print(f"\nRecommended RTSP URL: {best_uri}")
    else:
        print("Failed to connect to ONVIF service.")

if __name__ == "__main__":
    main()
