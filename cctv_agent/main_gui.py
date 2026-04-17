"""
CCTV Agent GUI - Main entry point.
Launches the headless service + GUI.
"""

import sys
import logging
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication

from cctv_agent.core.config_manager import ConfigManager
from cctv_agent.ui.main_window import MainWindow

# Setup logging
logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Launch GUI + service."""
    logger.info("=" * 60)
    logger.info("CCTV Agent GUI Starting")
    logger.info("=" * 60)

    # Start service process
    service_script = Path(__file__).parent / "main_service.py"
    logger.info(f"Starting service process: {service_script}")

    try:
        service_process = subprocess.Popen(
            [sys.executable, str(service_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"Service process started (PID: {service_process.pid})")
    except Exception as e:
        logger.error(f"Failed to start service process: {e}")
        service_process = None

    # Start GUI
    app = QApplication(sys.argv)

    config_manager = ConfigManager()
    window = MainWindow(config_manager, service_process)
    window.show()

    exit_code = app.exec()

    # Cleanup
    if service_process:
        logger.info("Terminating service process...")
        try:
            service_process.terminate()
            service_process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Failed to terminate service: {e}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
