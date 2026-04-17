from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout
)
from PySide6.QtCore import QTimer
import logging
from pathlib import Path

from cctv_agent import config as agent_config
from cctv_agent.services.db_manager import DBManager
from cctv_agent.workers.log_emitter import LogEmitter
from cctv_agent.ui.tabs_placeholder import (
    DiscoveryTab, CamerasTab, CloudConfigTab,
    CaptureLogsTab, QueueStatusTab, StatusTab
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main CCTV Agent window."""

    def __init__(self, config_manager, service_process=None):
        super().__init__()
        self.config_manager = config_manager
        self.service_process = service_process
        
        # Initialize services for GUI use
        self.db_manager = DBManager(agent_config.DB_FILE)
        self.log_emitter = LogEmitter(agent_config.LOGS_JSONL_FILE)

        self.setWindowTitle("CCTV Agent")
        self.setGeometry(100, 100, 1000, 700)

        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add actual tabs
        self.tab_discovery = DiscoveryTab(self.config_manager)
        self.tab_cameras = CamerasTab(self.config_manager)
        self.tab_cloud = CloudConfigTab(self.config_manager)
        self.tab_logs = CaptureLogsTab(self.log_emitter)
        self.tab_queue = QueueStatusTab(self.db_manager)
        self.tab_status = StatusTab()

        self.tabs.addTab(self.tab_status, "Overall Status")
        self.tabs.addTab(self.tab_cameras, "Cameras")
        self.tabs.addTab(self.tab_discovery, "Discovery")
        self.tabs.addTab(self.tab_cloud, "Cloud Config")
        self.tabs.addTab(self.tab_queue, "Queue")
        self.tabs.addTab(self.tab_logs, "Logs")

        # Setup refresh timer for logs and status
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_ui)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds

    def refresh_ui(self):
        """Refresh dynamic UI components."""
        self.tab_logs.update_logs(self.log_emitter.get_recent(20))
        self.tab_queue.update_status()
        
        # Simple health check
        service_running = self.service_process and self.service_process.poll() is None
        health = "Online" if service_running else "Offline (Service not running)"
        self.tab_status.update_status(health)

    def closeEvent(self, event):
        """Handle window close."""
        if self.service_process:
            logger.info("Shutting down service process...")
            try:
                self.service_process.terminate()
                # Use wait() for subprocess.Popen object
                self.service_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Failed to stop service: {e}")

        event.accept()
