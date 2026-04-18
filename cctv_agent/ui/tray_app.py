import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPainter, QColor, QAction
from PySide6.QtCore import QTimer, Qt

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from cctv_agent import config as agent_config

class CCTVStandaloneTray:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Paths
        self.status_file = agent_config.DATA_DIR / "status.json"
        self.bat_file = project_root / "run_cctv_service.bat"
        
        # Icons (generated dynamically)
        self.icons = {
            "running": self._generate_icon(Qt.green),
            "stopped": self._generate_icon(Qt.red),
            "error": self._generate_icon(Qt.yellow)
        }
        
        # Tray Icon setup
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.icons["stopped"])
        self.tray.setToolTip("CCTV Agent: Starting...")
        
        # Menu
        self.menu = QMenu()
        
        self.status_action = QAction("Status: Initializing...", None)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()
        
        open_storage = QAction("Open Storage Folder", None)
        open_storage.triggered.connect(self._open_storage)
        self.menu.addAction(open_storage)
        
        view_logs = QAction("View Logs", None)
        view_logs.triggered.connect(self._view_logs)
        self.menu.addAction(view_logs)
        
        restart_service = QAction("Restart Service", None)
        restart_service.triggered.connect(self._restart_service)
        self.menu.addAction(restart_service)
        
        self.menu.addSeparator()
        exit_action = QAction("Exit", None)
        exit_action.triggered.connect(self._exit)
        self.menu.addAction(exit_action)
        
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        
        # Timer for status updates
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(5000)  # Check every 5 seconds

    def _generate_icon(self, color):
        """Generate a simple circular QIcon."""
        from PySide6.QtGui import QPixmap
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.white)
        painter.drawEllipse(8, 8, 48, 48)
        painter.end()
        
        return QIcon(pixmap)

    def _update_status(self):
        status = "stopped"
        details = "Service Offline"
        
        if self.status_file.exists():
            try:
                # Check file staleness
                mtime = self.status_file.stat().st_mtime
                if time.time() - mtime > 120:
                    status = "stopped"
                    details = "Service Stalled"
                else:
                    with open(self.status_file, "r") as f:
                        data = json.load(f)
                        status = data.get("status", "stopped")
                        online = data.get("online_count", 0)
                        total = data.get("camera_count", 0)
                        details = f"Running ({online}/{total} active)"
            except Exception as e:
                status = "error"
                details = f"Status Error: {str(e)[:20]}"

        self.tray.setIcon(self.icons.get(status, self.icons["error"]))
        self.tray.setToolTip(f"CCTV Agent: {details}")
        self.status_action.setText(details)

    def _open_storage(self):
        if agent_config.QUEUE_DIR.exists():
            subprocess.Popen(f'explorer "{agent_config.QUEUE_DIR}"')

    def _view_logs(self):
        log_file = agent_config.LOGS_DIR / "service.log"
        if log_file.exists():
            subprocess.Popen(f'notepad "{log_file}"')

    def _restart_service(self):
        # Kill python processes and restart bat
        subprocess.Popen(["cmd", "/c", "taskkill /F /IM python.exe /T & start \"\" \"" + str(self.bat_file) + "\""], shell=True)

    def _exit(self):
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    tray = CCTVStandaloneTray()
    tray.run()
