import cv2
import time

def test_rtsp(urls):
    for url in urls:
        print(f"Testing {url}...")
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"  SUCCESS! Captured frame from {url}")
                cap.release()
                return url
            else:
                print(f"  Connected but failed to read frame from {url}")
        else:
            print(f"  Failed to open {url}")
        cap.release()
    return None

if __name__ == "__main__":
    ip = "192.168.1.12"
    creds = "admin:mohit123"
    
    # Common CP PLUS / Dahua RTSP paths
    paths = [
        "/cam/realmonitor?channel=1&subtype=1",
        "/live/channel0",
        "/live/ch1",
        "/onvif1",
        "/onvif/profile1/media.smp",
        ""
    ]
    
    ports = [554, 8000, 8899, 10554]
    
    urls = []
    for port in ports:
        for path in paths:
            urls.append(f"rtsp://{creds}@{ip}:{port}{path}")
            
    test_rtsp(urls)
