"""
Placeholder tab implementations.
To be expanded with full UI later.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QLineEdit, QSpinBox, QComboBox
)
from PySide6.QtCore import Qt


class DiscoveryTab(QWidget):
    """Camera discovery tab."""

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Camera Discovery"))
        layout.addWidget(QPushButton("Scan Network"))
        self.setLayout(layout)


class CamerasTab(QWidget):
    """Camera list and settings tab."""

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Configured Cameras"))

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Name", "IP", "Status"])
        layout.addWidget(table)

        self.setLayout(layout)


class CloudConfigTab(QWidget):
    """Cloud (GCS + Backend) configuration tab."""

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        settings = self.config_manager.get_cloud_settings()
        
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Backend API URL:"))
        self.api_url_edit = QLineEdit(settings.get("api_url", ""))
        layout.addWidget(self.api_url_edit)

        layout.addWidget(QLabel("API Key (provided by ProMe admin):"))
        self.api_key_edit = QLineEdit(settings.get("api_key", ""))
        layout.addWidget(self.api_key_edit)
        
        layout.addWidget(QLabel("GCS Bucket Name:"))
        self.gcs_bucket_edit = QLineEdit(settings.get("gcs_bucket", ""))
        layout.addWidget(self.gcs_bucket_edit)

        self.btn_save = QPushButton("💾 Save Settings")
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)

        self.btn_test_backend = QPushButton("🔍 Test Backend Connection")
        self.btn_test_backend.clicked.connect(self.test_backend)
        layout.addWidget(self.btn_test_backend)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def save_settings(self):
        settings = {
            "api_url": self.api_url_edit.text().strip(),
            "api_key": self.api_key_edit.text().strip(),
            "gcs_bucket": self.gcs_bucket_edit.text().strip()
        }
        if self.config_manager.save_cloud_settings(settings):
            self.status_label.setText("✅ Settings saved successfully")
        else:
            self.status_label.setText("❌ Failed to save settings")

    def test_backend(self):
        import httpx
        url = self.api_url_edit.text().strip()
        key = self.api_key_edit.text().strip()
        self.status_label.setText("Testing...")
        
        try:
            # We don't have a simple 'ping' so we'll just check the root or a safe endpoint
            response = httpx.get(f"{url}/", timeout=5)
            if response.status_code == 200:
                self.status_label.setText(f"✅ Connection successful (HTTP {response.status_code})")
            else:
                self.status_label.setText(f"⚠️ Server reached but returned HTTP {response.status_code}")
        except Exception as e:
            self.status_label.setText(f"❌ Connection failed: {str(e)[:50]}...")


class CaptureLogsTab(QWidget):
    """Capture logs viewer tab."""

    def __init__(self, log_emitter):
        super().__init__()
        self.log_emitter = log_emitter
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Recent Capture Events (last 10)"))

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        layout.addWidget(QPushButton("Clear Logs"))

        self.setLayout(layout)

    def update_logs(self, logs):
        """Update log display."""
        text = ""
        for log in logs:
            timestamp = log.get("timestamp", "")[:19]
            level = log.get("level", "").upper()
            message = log.get("message", "")
            text += f"{timestamp} [{level}] {message}\n"
        self.log_text.setText(text)


class QueueStatusTab(QWidget):
    """Queue status and manual controls tab."""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Queue Status"))

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)

        layout.addWidget(QPushButton("🔄 Refresh Status"))
        layout.addWidget(QPushButton("⬆️ Start Upload Now"))
        layout.addWidget(QPushButton("🗑️ Clear Failed Queue"))

        self.setLayout(layout)

    def update_status(self):
        """Update queue status display."""
        stats = self.db_manager.get_queue_stats()
        text = f"""Queue Status:
• Pending snapshots: {stats['pending_count']}
• Pending size: {stats['pending_size_bytes'] / (1024*1024):.1f} MB
• Last uploaded: {stats['last_uploaded_at'] or 'Never'}
"""
        self.status_text.setText(text)


class StatusTab(QWidget):
    """Overall status summary tab."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Overall Status"))

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)

        self.setLayout(layout)

    def update_status(self, health_status):
        """Update overall status."""
        self.status_text.setText(f"Health: {health_status}")
