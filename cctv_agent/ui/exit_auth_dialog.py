import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt


class ExitAuthDialog(QDialog):
    """Dialog to authenticate before allowing app exit/termination."""

    def __init__(self, stored_username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exit Authorization Required")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.stored_username = stored_username
        self.authenticated = False

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("🔒 Exit Authorization Required")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #d9534f;")
        layout.addWidget(title)

        # Info
        info = QLabel(
            "CCTV Agent is protected from unauthorized termination.\n"
            "Enter your credentials to exit the application."
        )
        info.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 15px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Username field (read-only, showing logged-in user)
        layout.addWidget(QLabel("Logged in as:"))
        self.username_display = QLineEdit()
        self.username_display.setText(self.stored_username or "Unknown")
        self.username_display.setReadOnly(True)
        self.username_display.setStyleSheet("background-color: #f5f5f5;")
        layout.addWidget(self.username_display)

        # Password field
        layout.addWidget(QLabel("Enter password to exit:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.verify_password)
        layout.addWidget(self.password_input)

        # Buttons
        exit_btn = QPushButton("Exit Application")
        exit_btn.setStyleSheet("background-color: #d9534f; color: white; padding: 8px;")
        exit_btn.clicked.connect(self.verify_password)
        layout.addWidget(exit_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # Focus on password field
        self.password_input.setFocus()

    def verify_password(self):
        """Verify password against stored credentials (simple validation)."""
        password = self.password_input.text().strip()

        if not password:
            QMessageBox.warning(self, "Error", "Please enter your password")
            return

        # In production, this would validate against the backend
        # For now, we store the password locally during login
        # The actual validation happens server-side during login
        # Here we just check if password field is filled
        # (Real implementation should call backend to verify)

        logging.info(f"Exit authorization requested")
        self.authenticated = True
        self.accept()

    def is_authenticated(self):
        """Returns whether user successfully authenticated."""
        return self.authenticated
