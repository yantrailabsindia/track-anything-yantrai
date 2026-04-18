import cv2
import time

def test_rtsp():
    url = "rtsp://admin:mohit123@192.168.1.12:5543/live/channel0"
    print(f"Testing URL: {url}")
    
    # Try with different API backends
    for backend in [None, cv2.CAP_FFMPEG]:
        print(f"\nTrying backend: {backend if backend else 'Auto'}")
        if backend:
            cap = cv2.VideoCapture(url, backend)
        else:
            cap = cv2.VideoCapture(url)
            
        if not cap.isOpened():
            print("Could not open video source")
            continue
            
        print("Successfully opened source. Waiting for frame...")
        
        ret, frame = cap.read()
        if ret:
            print(f"Success! Frame shape: {frame.shape}")
            cv2.imwrite("test_capture.jpg", frame)
            print("Saved test_capture.jpg")
            cap.release()
            return
        else:
            print("Failed to read frame")
        cap.release()

if __name__ == "__main__":
    test_rtsp()
