import cv2
import time
import os

# Force TCP for RTSP
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

url = "rtsp://admin:Puran234@192.168.1.33:554/Streaming/Channels/102"
print(f"Testing {url} with TCP...")
cap = cv2.VideoCapture(url)
if not cap.isOpened():
    print("Failed to open")
else:
    print("Opened successfully")
    # Some cameras need a delay
    time.sleep(1)
    ret, frame = cap.read()
    if ret:
        print("Captured successfully")
        cv2.imwrite("test_frame.jpg", frame)
    else:
        print("Failed to capture")
    cap.release()
