"""
VM Receiver Script
-----------------
Run this script on your remote VM to receive 5 FPS frames from the CCTV Agent.

Requirements:
pip install fastapi uvicorn aiofiles

How to run:
python vm_receiver.py
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
STORAGE_ROOT = Path("snapshots")
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
        # Create directory structure: snapshots / YYYY-MM-DD / <CAMERA-NO> / <FILE>
        # Note: captured_at is now provided in Indian Standard Time (IST)
        captured_dt = datetime.fromisoformat(captured_at)
        date_folder = captured_dt.strftime('%Y-%m-%d')
        
        logger.info(f"Receiving frame for {camera_id}: {filename} (IST: {captured_dt.strftime('%H:%M:%S')})")
        
        # Extract camera code (e.g., D01) from filename if possible, else use camera_id
        # Filename format: D01_20260418_192247123.jpg
        cam_code = filename.split('_')[0] if '_' in filename else camera_id
        
        save_dir = STORAGE_ROOT / date_folder / cam_code
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
    # Important: Ensure Port 8000 is open in your VM's firewall
    uvicorn.run(app, host="0.0.0.0", port=8000)
