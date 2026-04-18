"""
Discovery Tab - ONVIF camera discovery with multiple methods:
1. WS-Discovery (ONVIF auto-broadcast detection)
2. IP Range Scan (probes each IP in range for ONVIF)
3. Manual IP Entry (direct ONVIF connection to specific IP)
"""

import logging
import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal, QThread, QObject

from cctv_agent.core.onvif_client import ONVIFClient


def get_local_subnet():
    """Auto-detect the local subnet of this machine (e.g., '192.168.1')."""
    try:
        # Connect to external (doesn't send anything) to find route IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        parts = local_ip.split(".")
        return ".".join(parts[:3])  # "192.168.1"
    except Exception:
        return "192.168.1"


def probe_onvif(ip, port=80, timeout=2):
    """
    Quick TCP probe to check if ONVIF port is open on the given IP.
    Returns True if port is reachable.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            return result == 0
    except Exception:
        return False


class WSDiscoveryWorker(QObject):
    """Worker that runs WS-Discovery ONVIF broadcast scan."""
    device_found = Signal(str, str)  # ip, xaddr
    finished = Signal(int)  # count of devices found
    error = Signal(str)

    def __init__(self, timeout=10):
        super().__init__()
        self.timeout = timeout

    def run(self):
        try:
            from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
            from urllib.parse import urlparse

            wsd = WSDiscovery()
            wsd.start()
            try:
                services = wsd.searchServices(
                    timeout=self.timeout
                )

                seen = set()
                count = 0
                for service in services:
                    try:
                        xaddrs = service.getXAddrs()
                        if not xaddrs:
                            continue
                        xaddr = xaddrs[0]
                        if xaddr:
                            parsed = urlparse(xaddr)
                            ip = parsed.hostname
                        else:
                            ip = None

                        if ip and ip not in seen:
                            seen.add(ip)
                            count += 1
                            self.device_found.emit(ip, xaddr)
                    except Exception as e:
                        logging.debug(f"Failed to process WS-Discovery service: {e}")

                self.finished.emit(count)
            finally:
                wsd.stop()
        except Exception as e:
            logging.error(f"WS-Discovery failed: {e}")
            self.error.emit(str(e))


class IPRangeScanWorker(QObject):
    """Worker that scans a range of IPs for open ONVIF ports."""
    device_found = Signal(str, int)  # ip, port
    progress = Signal(int, int)  # current, total
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, ip_start, ip_end, ports=None):
        super().__init__()
        self.ip_start = ip_start
        self.ip_end = ip_end
        # Added 8899 and 8001; common ONVIF ports for Hikvision/Dahua/etc.
        self.ports = ports or [80, 8080, 8899, 8000, 8001, 2020]
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            start = int(ipaddress.ip_address(self.ip_start))
            end = int(ipaddress.ip_address(self.ip_end))

            if end < start:
                self.error.emit("Invalid IP range (end < start)")
                return

            all_ips = [str(ipaddress.ip_address(i)) for i in range(start, end + 1)]
            total = len(all_ips) * len(self.ports)
            found_count = 0
            completed = 0

            def check_ip_port(ip, port):
                if self._stop_flag:
                    return None
                if probe_onvif(ip, port, timeout=1):
                    return (ip, port)
                return None

            # Parallel scanning with thread pool
            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = []
                for ip in all_ips:
                    for port in self.ports:
                        if self._stop_flag:
                            break
                        futures.append(executor.submit(check_ip_port, ip, port))

                seen_ips = set()
                for future in as_completed(futures):
                    if self._stop_flag:
                        break
                    completed += 1
                    result = future.result()
                    if result:
                        ip, port = result
                        if ip not in seen_ips:
                            seen_ips.add(ip)
                            found_count += 1
                            self.device_found.emit(ip, port)
                    # Update progress every 10 items
                    if completed % 10 == 0:
                        self.progress.emit(completed, total)

            self.progress.emit(total, total)
            self.finished.emit(found_count)
        except Exception as e:
            logging.error(f"IP range scan failed: {e}")
            self.error.emit(str(e))


class ONVIFConnectWorker(QObject):
    """Worker that connects to an ONVIF device and retrieves info/channels."""
    success = Signal(dict)  # device_info dict
    error = Signal(str, str)  # ip, error message

    def __init__(self, ip, port, username, password):
        super().__init__()
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password

    def run(self):
        try:
            client = ONVIFClient(self.ip, self.username, self.password, self.port)
            if not client.connect():
                self.error.emit(self.ip, "Failed to connect (check credentials/time sync)")
                return

            info = client.get_device_info() or {}
            channels = client.get_channels()

            device_info = {
                "ip": self.ip,
                "port": self.port,
                "username": self.username,
                "password": self.password,
                "manufacturer": info.get("manufacturer", "Unknown"),
                "model": info.get("model", "Unknown"),
                "hw_id": info.get("hw_id", ""),
                "fw_version": info.get("fw_version", ""),
                "channels": channels
            }
            self.success.emit(device_info)
        except Exception as e:
            logging.error(f"ONVIF connect failed for {self.ip}: {e}")
            self.error.emit(self.ip, str(e))


class DiscoveryTab(QWidget):
    """Full-featured camera discovery tab with ONVIF WS-Discovery, IP range scan, and manual entry."""

    device_connected = Signal(dict)

    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        self.active_threads = []
        self.discovered_ips = {}  # {ip: {"port": int, "source": str}}

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("📹 Camera Discovery")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)

        info = QLabel(
            "Use any of the three methods below to discover ONVIF cameras on your network.\n"
            "ONVIF is the standard protocol most IP cameras support."
        )
        info.setStyleSheet("color: #666; font-size: 11px;")
        info.setWordWrap(True)
        main_layout.addWidget(info)

        # --- Method 1: ONVIF Auto-Discovery ---
        method1_box = QGroupBox("Method 1: ONVIF Auto-Discovery (WS-Discovery)")
        m1_layout = QHBoxLayout(method1_box)
        self.btn_ws_discover = QPushButton("🔍 Scan Network (ONVIF Broadcast)")
        self.btn_ws_discover.clicked.connect(self.start_ws_discovery)
        m1_layout.addWidget(self.btn_ws_discover)
        m1_layout.addWidget(QLabel("Fast but misses cameras with WS-Discovery disabled"))
        m1_layout.addStretch()
        main_layout.addWidget(method1_box)

        # --- Method 2: IP Range Scan ---
        method2_box = QGroupBox("Method 2: IP Range Scan (recommended for missed cameras)")
        m2_layout = QFormLayout(method2_box)

        local_subnet = get_local_subnet()
        range_layout = QHBoxLayout()
        self.ip_start = QLineEdit(f"{local_subnet}.1")
        self.ip_end = QLineEdit(f"{local_subnet}.254")
        range_layout.addWidget(QLabel("From:"))
        range_layout.addWidget(self.ip_start)
        range_layout.addWidget(QLabel("To:"))
        range_layout.addWidget(self.ip_end)
        m2_layout.addRow(range_layout)

        self.btn_range_scan = QPushButton("🌐 Scan IP Range")
        self.btn_range_scan.clicked.connect(self.start_range_scan)
        m2_layout.addRow(self.btn_range_scan)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        m2_layout.addRow(self.progress_bar)

        main_layout.addWidget(method2_box)

        # --- Method 3: Manual IP Entry ---
        method3_box = QGroupBox("Method 3: Add Camera by IP (manual entry)")
        m3_layout = QFormLayout(method3_box)

        self.manual_ip = QLineEdit()
        self.manual_ip.setPlaceholderText(f"{local_subnet}.100")
        m3_layout.addRow("Camera IP:", self.manual_ip)

        self.manual_port = QLineEdit("80")
        m3_layout.addRow("ONVIF Port:", self.manual_port)

        self.btn_add_manual = QPushButton("➕ Add Camera by IP")
        self.btn_add_manual.clicked.connect(self.add_manual_ip)
        m3_layout.addRow(self.btn_add_manual)

        main_layout.addWidget(method3_box)

        # --- Discovered Devices Table ---
        table_box = QGroupBox("Discovered Cameras")
        tbl_layout = QVBoxLayout(table_box)

        # Credentials for connection
        cred_layout = QHBoxLayout()
        cred_layout.addWidget(QLabel("Username:"))
        self.username_edit = QLineEdit("admin")
        self.username_edit.setMaximumWidth(120)
        cred_layout.addWidget(self.username_edit)
        cred_layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit("mohit123")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMaximumWidth(150)
        cred_layout.addWidget(self.password_edit)
        cred_layout.addStretch()
        tbl_layout.addLayout(cred_layout)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["IP Address", "Port", "Source", "Status", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        tbl_layout.addWidget(self.table)

        # Status label
        self.status_label = QLabel("Ready. Choose a discovery method above.")
        self.status_label.setStyleSheet("color: #555; font-style: italic;")
        tbl_layout.addWidget(self.status_label)

        main_layout.addWidget(table_box, 1)

    # ========== Compatibility method (called by F5 shortcut) ==========
    def start_scan(self):
        """Triggered by F5 / menu: runs ONVIF auto-discovery."""
        self.start_ws_discovery()

    # ========== Method 1: WS-Discovery ==========
    def start_ws_discovery(self):
        self.status_label.setText("🔍 Scanning network via ONVIF WS-Discovery...")
        self.btn_ws_discover.setEnabled(False)

        thread = QThread()
        worker = WSDiscoveryWorker(timeout=5)
        worker.moveToThread(thread)

        worker.device_found.connect(lambda ip, xaddr: self._add_discovered(ip, 80, "WS-Discovery"))
        worker.finished.connect(lambda count: self._on_scan_finished("WS-Discovery", count))
        worker.error.connect(self._on_scan_error)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda: self.btn_ws_discover.setEnabled(True))
        thread.finished.connect(thread.deleteLater)

        self.active_threads.append((thread, worker))
        thread.start()

    # ========== Method 2: IP Range Scan ==========
    def start_range_scan(self):
        ip_start = self.ip_start.text().strip()
        ip_end = self.ip_end.text().strip()

        try:
            ipaddress.ip_address(ip_start)
            ipaddress.ip_address(ip_end)
        except ValueError:
            QMessageBox.warning(self, "Invalid IP", "Please enter valid IP addresses.")
            return

        self.status_label.setText(f"🌐 Scanning {ip_start} → {ip_end} for ONVIF cameras...")
        self.btn_range_scan.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        thread = QThread()
        worker = IPRangeScanWorker(ip_start, ip_end)
        worker.moveToThread(thread)

        worker.device_found.connect(lambda ip, port: self._add_discovered(ip, port, "IP Range"))
        worker.progress.connect(lambda c, t: self.progress_bar.setValue(int(c * 100 / max(t, 1))))
        worker.finished.connect(lambda count: self._on_scan_finished("IP Range Scan", count))
        worker.error.connect(self._on_scan_error)

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda: (
            self.btn_range_scan.setEnabled(True),
            self.progress_bar.setVisible(False)
        ))
        thread.finished.connect(thread.deleteLater)

        self.active_threads.append((thread, worker))
        thread.start()

    # ========== Method 3: Manual IP ==========
    def add_manual_ip(self):
        ip = self.manual_ip.text().strip()
        port_str = self.manual_port.text().strip()

        try:
            ipaddress.ip_address(ip)
            port = int(port_str)
        except Exception:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid IP and port.")
            return

        self._add_discovered(ip, port, "Manual")
        self.status_label.setText(f"✓ Added {ip}:{port} manually. Click 'Connect' to authenticate.")

    # ========== Helpers ==========
    def _add_discovered(self, ip, port, source):
        """Add a discovered device to the table (dedup by IP)."""
        if ip in self.discovered_ips:
            return
        self.discovered_ips[ip] = {"port": port, "source": source}

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(ip))
        self.table.setItem(row, 1, QTableWidgetItem(str(port)))
        self.table.setItem(row, 2, QTableWidgetItem(source))
        self.table.setItem(row, 3, QTableWidgetItem("Pending"))

        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(lambda _, i=ip, p=port, r=row: self._connect_device(i, p, r))
        self.table.setCellWidget(row, 4, connect_btn)

    def _connect_device(self, ip, port, row):
        username = self.username_edit.text().strip() or "admin"
        password = self.password_edit.text() or "admin"

        self.table.item(row, 3).setText("Connecting...")
        cell_widget = self.table.cellWidget(row, 4)
        if cell_widget:
            cell_widget.setEnabled(False)

        thread = QThread()
        worker = ONVIFConnectWorker(ip, port, username, password)
        worker.moveToThread(thread)

        worker.success.connect(lambda info: self._on_device_connected(info, row))
        worker.error.connect(lambda ip_err, msg: self._on_connect_error(ip_err, msg, row))
        thread.started.connect(worker.run)
        worker.success.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self.active_threads.append((thread, worker))
        thread.start()

    def _on_device_connected(self, device_info, row):
        ip = device_info["ip"]
        manufacturer = device_info.get("manufacturer", "")
        model = device_info.get("model", "")
        channels = len(device_info.get("channels", []))
        self.table.item(row, 3).setText(f"✓ {manufacturer} {model} ({channels} channels)")

        cell_widget = self.table.cellWidget(row, 4)
        if cell_widget:
            cell_widget.setText("Added")
            cell_widget.setEnabled(False)

        self.device_connected.emit(device_info)
        self.status_label.setText(f"✓ Connected to {ip} — {manufacturer} {model}")

    def _on_connect_error(self, ip, msg, row):
        self.table.item(row, 3).setText(f"✗ {msg[:50]}")
        cell_widget = self.table.cellWidget(row, 4)
        if cell_widget:
            cell_widget.setText("Retry")
            cell_widget.setEnabled(True)

    def _on_scan_finished(self, method, count):
        self.status_label.setText(f"✓ {method} complete. Found {count} potential cameras.")

    def _on_scan_error(self, msg):
        self.status_label.setText(f"✗ Scan failed: {msg}")
