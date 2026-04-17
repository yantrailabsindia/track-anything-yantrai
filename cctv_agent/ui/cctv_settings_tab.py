import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
                             QLabel, QSpinBox, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal


class CCTVSettingsTab(QWidget):
    """CCTV Settings Tab for camera selection and per-camera FPS configuration."""

    settings_changed = Signal(dict)  # Emitted when camera settings change

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.devices_data = {}  # { ip: device_info }
        self.camera_fps_widgets = {}  # { (ip, ch_num): QSpinBox }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Title
        title = QLabel("CCTV Capture Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Info
        info = QLabel("Select cameras to capture frames and configure frame rate for each camera.")
        info.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info)

        # Tree with cameras
        layout.addWidget(QLabel("Available Cameras:"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Camera")
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Camera", "Enabled", "FPS", ""])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 60)
        layout.addWidget(self.tree)

        # Save Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def set_devices(self, devices_data):
        """Populate camera list from discovered devices."""
        self.devices_data = devices_data
        self.tree.clear()
        self.camera_fps_widgets.clear()

        # Load saved settings
        cloud_settings = self.config_manager.get_cloud_settings()
        active_streams = set(cloud_settings.get("active_streams", []))

        for ip, device_info in devices_data.items():
            # Device root item
            device_item = QTreeWidgetItem(self.tree)
            device_item.setText(0, f"{ip} ({device_info.get('manufacturer', 'Unknown')})")
            device_item.setExpanded(True)

            # Channels
            for ch in device_info.get('channels', []):
                ch_num = ch['channel_number']
                ch_name = ch.get('name', f"Channel {ch_num}")
                key = f"{ip}:{ch_num}"

                ch_item = QTreeWidgetItem(device_item)
                ch_item.setText(0, ch_name)
                ch_item.setData(0, Qt.UserRole, (ip, ch_num))

                # Enabled checkbox
                ch_item.setCheckState(1, Qt.Checked if key in active_streams else Qt.Unchecked)

                # FPS spinner
                fps_box = QSpinBox()
                fps_box.setMinimum(1)
                fps_box.setMaximum(30)
                fps_box.setValue(ch.get('frame_rate_fps', 10))
                fps_box.setSuffix(" FPS")
                self.tree.setItemWidget(ch_item, 2, fps_box)

                self.camera_fps_widgets[key] = fps_box

    def save_settings(self):
        """Save camera selection and FPS settings."""
        try:
            active_streams = []

            # Iterate through all camera items and collect settings
            for device_idx in range(self.tree.topLevelItemCount()):
                device_item = self.tree.topLevelItem(device_idx)

                for ch_idx in range(device_item.childCount()):
                    ch_item = device_item.child(ch_idx)
                    data = ch_item.data(0, Qt.UserRole)

                    if not data:
                        continue

                    ip, ch_num = data
                    key = f"{ip}:{ch_num}"
                    enabled = (ch_item.checkState(1) == Qt.Checked)

                    if enabled:
                        active_streams.append(key)

                        # Save FPS for this camera
                        fps_box = self.camera_fps_widgets.get(key)
                        if fps_box and (ip, ch_num) in [(d_ip, c['channel_number'])
                                                         for d_ip, d in self.devices_data.items()
                                                         for c in d.get('channels', [])]:
                            # Update device info with new FPS
                            device = self.devices_data.get(ip)
                            if device:
                                for ch in device.get('channels', []):
                                    if ch['channel_number'] == ch_num:
                                        ch['frame_rate_fps'] = fps_box.value()

            # Save to config
            cloud_settings = self.config_manager.get_cloud_settings()
            cloud_settings["active_streams"] = active_streams
            self.config_manager.save_cloud_settings(cloud_settings)

            # Emit signal
            self.settings_changed.emit({
                'active_streams': active_streams,
                'devices': self.devices_data
            })

            QMessageBox.information(self, "Success", "CCTV settings saved successfully!")
            logging.info(f"CCTV settings saved: {len(active_streams)} cameras enabled")

        except Exception as e:
            logging.error(f"Failed to save CCTV settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
