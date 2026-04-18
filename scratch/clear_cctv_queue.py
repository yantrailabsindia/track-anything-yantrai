import sys
import os
import logging
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Mock log emitter for the worker
class MockLogEmitter:
    def emit(self, level, category, message, **kwargs):
        print(f"[{level.upper()}] {category}: {message}")

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

try:
    from cctv_agent.core.config_manager import ConfigManager
    from cctv_agent.services.db_manager import DBManager
    from cctv_agent.workers.upload_worker import UploadWorker
    
    # 1. Initialize Managers
    print("Initializing Managers...")
    config_manager = ConfigManager()
    
    # Correct path to local agent DB on Windows
    db_path = Path.home() / "CCTVAgent" / "cctv_agent.db"
    db_manager = DBManager(db_path)
    
    # 2. Setup Worker
    print("Setting up UploadWorker...")
    worker = UploadWorker(
        config_manager=config_manager,
        db_manager=db_manager,
        log_emitter=MockLogEmitter()
    )
    
    # 3. Verify mohit's credentials in config
    user_info = config_manager.get_user_info()
    cloud_settings = config_manager.get_cloud_settings()
    print(f"Verified User: {user_info.get('username')} (ID: {user_info.get('user_id')})")
    print(f"API Key in Config: {cloud_settings.get('api_key')}")
    print(f"Target VM: {user_info.get('api_url')}")
    
    # 4. Trigger Batch Upload
    print("\n>>> STARTING BATCH UPLOAD <<<")
    worker._do_upload()
    print("\n>>> BATCH UPLOAD PROCESS COMPLETE <<<")
    
    # 5. Check remaining queue
    stats = db_manager.get_queue_stats()
    print(f"Remaining Pending: {stats.get('pending_count')}")

except Exception as e:
    import traceback
    print(f"CRITICAL ERROR: {e}")
    traceback.print_exc()
