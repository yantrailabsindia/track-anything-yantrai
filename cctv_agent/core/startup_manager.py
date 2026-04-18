"""
Manages CCTV Agent startup persistence on Windows.
Handles registry entries to auto-start on system boot.
"""

import logging
import os
import sys
import winreg
from pathlib import Path


class StartupManager:
    """Manages auto-start registry entries for CCTV Agent."""

    APP_NAME = "CCTVAgent"
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @staticmethod
    def get_exe_path():
        """Get the path to the executable."""
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            return sys.executable
        else:
            # Running as Python script - return the spec exe path
            base_path = Path(__file__).parent.parent.parent
            return str(base_path / "dist" / "CCTVAgent.exe")

    @staticmethod
    def enable_startup():
        """Register CCTV Agent to run on Windows startup."""
        try:
            exe_path = StartupManager.get_exe_path()

            # Validate that exe exists
            if not os.path.exists(exe_path):
                logging.warning(f"Cannot enable startup: exe not found at {exe_path}")
                return False

            # Open registry key for writing
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                StartupManager.REGISTRY_PATH,
                0,
                winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(
                    key,
                    StartupManager.APP_NAME,
                    0,
                    winreg.REG_SZ,
                    f'"{exe_path}"'  # Quote path in case of spaces
                )

            logging.info(f"✓ CCTV Agent registered for auto-start")
            logging.info(f"  Path: {exe_path}")
            return True

        except PermissionError:
            logging.error("Failed to enable startup: Permission denied (may require admin)")
            return False
        except Exception as e:
            logging.error(f"Failed to enable startup: {e}")
            return False

    @staticmethod
    def disable_startup():
        """Unregister CCTV Agent from Windows startup."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                StartupManager.REGISTRY_PATH,
                0,
                winreg.KEY_WRITE
            ) as key:
                try:
                    winreg.DeleteValue(key, StartupManager.APP_NAME)
                    logging.info("✓ CCTV Agent removed from auto-start")
                    return True
                except FileNotFoundError:
                    logging.info("CCTV Agent was not in startup registry")
                    return True

        except PermissionError:
            logging.error("Failed to disable startup: Permission denied")
            return False
        except Exception as e:
            logging.error(f"Failed to disable startup: {e}")
            return False

    @staticmethod
    def is_enabled():
        """Check if CCTV Agent is registered for auto-start."""
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                StartupManager.REGISTRY_PATH,
                0,
                winreg.KEY_READ
            ) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, StartupManager.APP_NAME)
                    return bool(value)
                except FileNotFoundError:
                    return False

        except Exception as e:
            logging.warning(f"Failed to check startup status: {e}")
            return False

    @staticmethod
    def get_startup_status():
        """Get human-readable startup status."""
        enabled = StartupManager.is_enabled()
        return "Enabled (runs on startup)" if enabled else "Disabled"
