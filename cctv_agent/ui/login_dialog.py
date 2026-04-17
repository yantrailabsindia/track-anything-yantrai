import logging
import httpx
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt


class LoginDialog(QDialog):
    """Dialog for user to log in with webapp credentials."""

    def __init__(self, api_url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login to CCTV Agent")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.api_url = api_url
        self.user_data = None
        self.token = None

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Webapp Account Login")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Info
        info = QLabel("Log in with your webapp credentials to enable CCTV frame capture")
        info.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 20px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Username field
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        layout.addWidget(self.username_input)

        # Password field
        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # API URL field
        layout.addWidget(QLabel("API Server URL:"))
        self.api_url_input = QLineEdit()
        self.api_url_input.setText(self.api_url or "http://localhost:8000")
        self.api_url_input.setPlaceholderText("http://localhost:8000")
        layout.addWidget(self.api_url_input)

        # Buttons
        button_layout = QHBoxLayout()

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(login_btn)

        skip_btn = QPushButton("Skip for Now")
        skip_btn.clicked.connect(self.reject)
        button_layout.addWidget(skip_btn)

        layout.addLayout(button_layout)

        # Connect Enter key to login
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        """Attempt to log in with provided credentials."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        api_url = self.api_url_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return

        if not api_url:
            QMessageBox.warning(self, "Error", "Please enter API server URL")
            return

        try:
            # Attempt login
            login_url = f"{api_url.rstrip('/')}/api/auth/login"
            logging.info(f"Attempting login to {login_url}")

            response = httpx.post(
                login_url,
                json={"username": username, "password": password},
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.user_data = data.get("user")

                if self.user_data and self.token:
                    logging.info(f"Login successful for user {self.user_data.get('username')}")
                    self.api_url = api_url  # Save the API URL
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Invalid response from server")
            else:
                error_msg = response.json().get("detail", "Login failed")
                QMessageBox.critical(self, "Login Failed", error_msg)
                logging.error(f"Login failed: {error_msg}")

        except httpx.TimeoutException:
            QMessageBox.critical(self, "Error", f"Connection timeout. Check API URL:\n{api_url}")
        except httpx.ConnectError:
            QMessageBox.critical(self, "Error", f"Cannot connect to server:\n{api_url}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login error: {str(e)}")
            logging.error(f"Login error: {e}")
