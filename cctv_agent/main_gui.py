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

def get_old_pid():
    """
    Get the PID of any previously running instance (without killing it).
    Returns the old PID if found, None otherwise.
    """
    pid_file = os.path.expanduser("~/CCTVAgent/app.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None

def kill_old_instance(old_pid):
    """
    Kill the old instance after user has authenticated.
    Called after successful login to ensure smooth transition.
    """
    if old_pid and old_pid != os.getpid():
        try:
            subprocess.run(['taskkill', '/F', '/PID', str(old_pid)],
                          capture_output=True)
            time.sleep(2)  # Wait for old process to fully terminate
            logging.info(f"Terminated old instance (PID: {old_pid}) after authentication")
        except Exception as e:
            logging.warning(f"Failed to terminate old instance: {e}")

def save_current_pid():
    """
    Save the current process PID to ensure single instance.
    """
    pid_file = os.path.expanduser("~/CCTVAgent/app.pid")
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    try:
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logging.error(f"Failed to save PID file: {e}")

def main():
    setup_logging()
    old_pid = get_old_pid()
    save_current_pid()

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

    window = MainWindow(config_manager, old_pid=old_pid)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
