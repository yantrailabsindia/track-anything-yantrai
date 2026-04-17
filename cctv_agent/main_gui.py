import sys 
import logging
import os
import signal
import subprocess
import time
from pathlib import Path

# --- ROBUST ABSOLUTE PACKAGE INITIALIZATION ---
try:
    # Get the project root (parent of 'cctv_agent')
    script_path = Path(__file__).resolve()
    # If we are in cctv_agent/main_gui.py, the package root is the parent dir
    package_root = script_path.parent.parent
    
    # Add project root to sys.path so 'import cctv_agent' works
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
        
except Exception as e:
    print(f"Critical error during path initialization: {e}")

# Import using the full package name
try:
    from PySide6.QtWidgets import QApplication
    from cctv_agent.ui.main_window import MainWindow
    from cctv_agent.core.config_manager import ConfigManager
except ModuleNotFoundError as e:
    print("\n" + "!"*60)
    print(f" IMPORT ERROR: {e}")
    print(f" Package Root Detected: {package_root if 'package_root' in locals() else 'Unknown'}")
    print(f" Current sys.path:")
    for p in sys.path:
        print(f"  - {p}")
    print("!"*60 + "\n")
    raise

def setup_logging():
    log_dir = os.path.expanduser("~/CCTVAgent/logs")
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "app.log")),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Starting CCTV Agent Application...")

def ensure_single_instance():
    """
    Ensures only one instance of the app is running.
    Kills the old instance if it exists.
    """
    pid_file = os.path.expanduser("~/CCTVAgent/app.pid")
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    
    current_pid = os.getpid()
    
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            
            # Check if old process is still running
            # In Windows, we can use TASKLIST or just try to signal it
            # But taskkill /PID is more reliable for killing
            if old_pid != current_pid:
                # Use taskkill to kill the old PID
                subprocess.run(['taskkill', '/F', '/PID', str(old_pid)],
                              capture_output=True)
                time.sleep(2)  # Wait for old process to fully terminate
                logging.info(f"Terminated old instance (PID: {old_pid})")
        except Exception as e:
            # If the PID is not found or other error, ignore
            pass
            
    # Save the current PID
    try:
        with open(pid_file, "w") as f:
            f.write(str(current_pid))
    except Exception as e:
        logging.error(f"Failed to save PID file: {e}")

def main():
    setup_logging()
    ensure_single_instance()
    
    app = QApplication(sys.argv)
    app.setApplicationName("CCTV Agent")
    
    # Load Stylesheet
    try:
        style_path = os.path.join(os.path.dirname(__file__), "ui", "styles.qss")
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        logging.error(f"Failed to load stylesheet: {e}")
    
    config_manager = ConfigManager()
    
    window = MainWindow(config_manager)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
