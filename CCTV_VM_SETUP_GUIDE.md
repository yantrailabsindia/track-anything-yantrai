# CCTV VM Receiver Setup Guide

This guide contains everything you need to set up a high-performance frame receiving point on a remote VM. This receiver is designed to handle 5 FPS streams from 16 cameras simultaneously.

## 1. Prerequisites

The receiver requires Python 3.8+ and a few lightweight dependencies to handle high-concurrency file writing.

### Installation Command
Run the following on your VM:
```bash
pip install fastapi uvicorn aiofiles python-multipart httpx
```

## 2. Receiver Script (`vm_receiver.py`)

Create a file named `vm_receiver.py` on the VM and paste the following content:

```python
"""
VM Receiver Script
-----------------
Run this script on your remote VM to receive 5 FPS frames from the CCTV Agent.
"""

import os
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
import aiofiles
from datetime import datetime
import uvicorn
import logging

# Configure storage path on VM
STORAGE_ROOT = Path("captured_frames")
STORAGE_ROOT.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="CCTV Frame Receiver")

@app.post("/upload")
async def receive_frame(
    background_tasks: BackgroundTasks,
    camera_id: str = Form(...),
    captured_at: str = Form(...),
    filename: str = Form(...),
    org_id: str = Form("default"),
    file: UploadFile = File(...)
):
    """
    Receives frame from CCTV agent and saves to disk.
    """
    try:
        # Create directory structure: captured_frames/org_id/camera_id/YYYY/MM/DD/
        captured_dt = datetime.fromisoformat(captured_at)
        date_folder = captured_dt.strftime('%Y/%m/%d')
        save_dir = STORAGE_ROOT / org_id / camera_id / date_folder
        save_dir.mkdir(parents=True, exist_ok=True)
        
        save_path = save_dir / filename
        
        # Read the file content
        content = await file.read()
        
        # Async write to disk (background task to keep response fast)
        background_tasks.add_task(save_to_disk, save_path, content)
        
        return JSONResponse(content={"status": "success", "file": str(save_path)}, status_code=200)
    
    except Exception as e:
        logger.error(f"Error receiving frame from {camera_id}: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

async def save_to_disk(path: Path, content: bytes):
    """Utility to write bytes to disk asynchronously."""
    async with aiofiles.open(path, mode='wb') as f:
        await f.write(content)

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    # Run on all interfaces (Port 8000)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 3. Firewall Configuration

For the agent to "tunnel" frames to the VM, **Port 8000** must be open.

- **Cloud Provider (e.g., Google Cloud/AWS):** Add an Inbound Firewall Rule to allow **TCP Port 8000** from all IP addresses (or specifically from the Agent's IP).
- **OS Firewall (Ubuntu/Linux):**
  ```bash
  sudo ufw allow 8000/tcp
  ```

## 4. Running the Service

### Option A: Direct Run (For Testing)
```bash
python vm_receiver.py
```

### Option B: Background Run (Recommended)
Use `nohup` or `screen` to keep it running after you disconnect from SSH:
```bash
nohup python vm_receiver.py > receiver.log 2>&1 &
```

## 5. Verification
Once the service is running, you can test it by visiting:
`http://<VM_IP>:8000/health`

Valid snapshots will begin appearing in the `captured_frames/` directory on the VM, organized by Organization, Camera ID, and Date.

---
**Note:** The CCTV Agent on the local machine uses a **10-minute local buffer**. It will only start sending frames that are at least 10 minutes old.
