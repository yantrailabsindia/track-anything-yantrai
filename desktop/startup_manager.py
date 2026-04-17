"""
Windows Startup Registration Manager — handles auto-start on system boot
"""
import winreg
import sys
from pathlib import Path
from desktop.config import DATA_DIR, APP_NAME

STARTUP_CONFIG_FILE = DATA_DIR / "startup_config.json"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REGISTRY_ENTRY_NAME = APP_NAME  # "ProMe"


def get_executable_path():
    """Get the full path to ProMe.exe, handling both PyInstaller and dev modes"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller exe
        exe_path = Path(sys.executable).resolve()
    else:
        # Development mode - look for dist/ProMe.exe
        project_root = Path(__file__).resolve().parent.parent
        exe_path = project_root / "dist" / "ProMe.exe"

    return exe_path


def validate_executable_exists(exe_path):
    """Check if executable exists"""
    return exe_path.exists()


def enable_startup():
    """
    Register ProMe to start on Windows startup
    Returns: (success: bool, message: str)
    """
    try:
        exe_path = get_executable_path()

        if not validate_executable_exists(exe_path):
            return False, f"Executable not found: {exe_path}"

        # Convert to string and ensure quotes for paths with spaces
        exe_path_str = str(exe_path.resolve())

        # Open registry key for current user
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REGISTRY_KEY,
                0,
                winreg.KEY_SET_VALUE
            )
        except PermissionError:
            return False, "Permission denied: Cannot write to registry (try running as admin)"

        # Set the registry value
        winreg.SetValueEx(key, REGISTRY_ENTRY_NAME, 0, winreg.REG_SZ, exe_path_str)
        winreg.CloseKey(key)

        return True, f"ProMe successfully registered to start on Windows startup"

    except PermissionError:
        return False, "Permission denied: Cannot write to registry"
    except Exception as e:
        return False, f"Error enabling startup: {str(e)}"


def disable_startup():
    """
    Remove ProMe from Windows startup registry
    Returns: (success: bool, message: str)
    """
    try:
        # Open registry key for current user
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REGISTRY_KEY,
                0,
                winreg.KEY_SET_VALUE
            )
        except PermissionError:
            return False, "Permission denied: Cannot write to registry (try running as admin)"

        # Delete the registry value
        try:
            winreg.DeleteValue(key, REGISTRY_ENTRY_NAME)
        except FileNotFoundError:
            # Entry doesn't exist - that's fine, return success
            winreg.CloseKey(key)
            return True, "ProMe startup registration already disabled"

        winreg.CloseKey(key)
        return True, "ProMe startup registration removed successfully"

    except PermissionError:
        return False, "Permission denied: Cannot write to registry"
    except Exception as e:
        return False, f"Error disabling startup: {str(e)}"


def is_startup_enabled():
    """
    Check if ProMe is registered to start on Windows startup
    Returns: bool
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_READ
        )

        try:
            value, regtype = winreg.QueryValueEx(key, REGISTRY_ENTRY_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False

    except Exception:
        # If there's any error accessing registry, assume not enabled
        return False


def mark_startup_prompt_shown():
    """Mark that we've shown the first-run startup prompt"""
    import json
    try:
        config = {}
        if STARTUP_CONFIG_FILE.exists():
            with open(STARTUP_CONFIG_FILE, 'r') as f:
                config = json.load(f)

        config['startup_prompt_shown'] = True

        with open(STARTUP_CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error marking startup prompt shown: {e}")


def has_startup_prompt_been_shown():
    """Check if we've already shown the first-run startup prompt"""
    import json
    try:
        if STARTUP_CONFIG_FILE.exists():
            with open(STARTUP_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('startup_prompt_shown', False)
    except Exception as e:
        print(f"Error checking startup prompt flag: {e}")

    return False
