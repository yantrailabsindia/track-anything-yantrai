import threading
import time
import sys
import os
import psutil
from pathlib import Path
import platform

# ── DASHBOARD MODE CHECK (must be FIRST, before anything else) ──
if __name__ == "__main__" and "--dashboard" in sys.argv:
    try:
        from desktop.ui.dashboard_window import DashboardWindow
        username = "User"
        org_name = "Personal"
        args = sys.argv[1:]
        for i, arg in enumerate(args):
            if arg == "--username" and i + 1 < len(args):
                username = args[i + 1]
            elif arg == "--org" and i + 1 < len(args):
                org_name = args[i + 1]

        dashboard = DashboardWindow(username=username, org_name=org_name)
        dashboard.run()
    except Exception as e:
        print(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
    sys.exit(0)

# ── MAIN AGENT MODE (only runs if NOT dashboard) ──

# Setup debug logging to file
if getattr(sys, 'frozen', False):
    _base = Path(sys.executable).resolve().parent.parent
else:
    _base = Path(__file__).parent.parent
DEBUG_LOG = _base / "data" / "debug.log"
DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)


def hide_console_window():
    """Hide the console window on Windows."""
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.kernel32.GetConsoleWindow.restype = ctypes.c_void_p
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        except Exception as e:
            log_debug(f"Could not hide console window: {e}")


def log_debug(msg):
    """Write debug messages to both console and file"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass


def kill_existing_agent():
    """Kill any existing ProMe agent processes (NOT dashboard subprocesses)"""
    current_pid = os.getpid()
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.pid == current_pid:
                    continue

                proc_name = proc.info.get("name", "").lower()
                cmdline = proc.info.get("cmdline", [])
                cmdline_str = " ".join(cmdline).lower() if cmdline else ""

                # Skip dashboard subprocesses
                if "--dashboard" in cmdline_str:
                    continue

                is_prome = (
                    "prome.exe" in proc_name or
                    "run_agent.py" in cmdline_str or
                    ("python.exe" in proc_name and "run_agent" in cmdline_str)
                )

                if is_prome:
                    log_debug(f"Terminating existing ProMe instance (PID: {proc.pid})")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                        log_debug(f"Existing instance terminated")
                    except psutil.TimeoutExpired:
                        log_debug(f"Forcefully killing existing instance")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        log_debug(f"Error checking for existing instances: {e}")


log_debug("=== ProMe Agent Starting ===")
kill_existing_agent()
log_debug("Existing instance check completed")

try:
    from desktop.trackers.window_tracker import WindowTracker
    from desktop.trackers.input_tracker import InputTracker
    from desktop.trackers.screenshot_tracker import ScreenshotTracker
    from desktop.trackers.telemetry_tracker import TelemetryTracker
    from desktop.trackers.server_uploader import ServerUploader
    from desktop.ui.tray import TrayIcon
    from desktop.ui.login_window import require_login
    from desktop import startup_manager
    log_debug("All imports successful")
except Exception as e:
    log_debug(f"Import error: {e}")
    import traceback
    log_debug(traceback.format_exc())
    raise


def run_agent_session(token, user_id, username, org_name):
    """
    Run a single agent session (login -> tracking -> logout).
    Returns: True if should continue (logout+relogin), False if should exit
    """
    try:
        log_debug(f"Starting session for user: {username}")

        # Hide console window after successful login
        log_debug("Hiding console window...")
        hide_console_window()

        # Initialize SessionManager for this session
        from desktop.trackers.session_manager import get_session_manager
        from desktop.trackers.server_uploader import get_or_create_device_id
        session_manager = get_session_manager()
        device_id = get_or_create_device_id()
        session_manager.start_session(user_id, username, device_id)
        log_debug(f"Session initialized: {session_manager.get_session_id()}")

        # Initialize data store and load historical data
        from desktop.trackers.data_store import get_data_store
        data_store = get_data_store()
        data_store.load_daily_totals_from_log()
        log_debug("Data store initialized")

        stop_event = threading.Event()
        pause_event = threading.Event()  # set = paused
        logout_event = threading.Event()  # set when user requests logout

        # Initialize trackers
        window_tracker = WindowTracker()
        input_tracker = InputTracker()
        screenshot_tracker = ScreenshotTracker()
        telemetry_tracker = TelemetryTracker()
        server_uploader = ServerUploader(auth_token=token, user_id=user_id)

        # Define threads — each tracker respects pause_event
        threads = [
            threading.Thread(target=window_tracker.run, args=(stop_event, pause_event), daemon=True),
            threading.Thread(target=input_tracker.run, args=(stop_event, pause_event), daemon=True),
            threading.Thread(target=screenshot_tracker.run, args=(stop_event, pause_event), daemon=True),
            threading.Thread(target=telemetry_tracker.run, args=(stop_event, pause_event), daemon=True),
            threading.Thread(target=server_uploader.run, args=(stop_event, pause_event), daemon=True),
        ]

        # Start tracking threads
        for t in threads:
            t.start()

        def signal_stop():
            log_debug("Stopping trackers...")
            stop_event.set()

        def signal_logout():
            log_debug("Logout requested, stopping trackers...")
            logout_event.set()
            stop_event.set()

        # Store threads reference for cleanup later
        agent_threads = threads

        # Start tray icon with pause_event (blocking)
        log_debug("Creating TrayIcon...")
        tray = TrayIcon(
            stop_callback=signal_stop,
            pause_event=pause_event,
            username=username,
            org_name=org_name,
            logout_callback=signal_logout
        )
        log_debug("Starting tray...")
        tray.run()

        # Wait for tracker threads to finish (with timeout)
        log_debug("Waiting for trackers to stop...")
        for t in agent_threads:
            t.join(timeout=5)

        # Tray exited — check if it was logout or quit
        if logout_event.is_set():
            log_debug("User logged out, ending session")
            session_manager.end_session()
            from desktop.auth import logout
            logout()
            return True  # Continue to re-show login
        else:
            log_debug("User quit application, ending session")
            session_manager.end_session()
            return False  # Exit completely

    except Exception as e:
        log_debug(f"ERROR in run_agent_session: {e}")
        import traceback
        log_debug(traceback.format_exc())
        raise


def main():
    try:
        log_debug("Starting main function...")

        # Main loop — allows logout + re-login
        while True:
            # Check for cached credentials (persistent login)
            from desktop.auth import is_authenticated, load_auth_token

            if is_authenticated():
                log_debug("Cached credentials found, loading session...")
                token, user_id, username = load_auth_token()
            else:
                log_debug("No cached credentials, showing login window...")
                token, user_id, username = require_login()

                if not token:
                    log_debug("Login cancelled or failed by user")
                    return

            log_debug(f"Session starting for user: {username}")

            # Get org_name from auth file
            org_name = None
            try:
                import json
                from desktop.config import DATA_DIR
                auth_file = DATA_DIR / "auth.json"
                if auth_file.exists():
                    with open(auth_file, "r") as f:
                        auth_data = json.load(f)
                        org_name = auth_data.get("org_name")
            except Exception:
                org_name = None

            # Show first-run startup prompt (only once per user)
            if not startup_manager.has_startup_prompt_been_shown():
                try:
                    from tkinter import messagebox
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)

                    response = messagebox.askyesno(
                        "ProMe Startup",
                        "Enable ProMe to start automatically on Windows startup?\n\n"
                        "ProMe works best as a background service that runs continuously."
                    )
                    root.destroy()

                    if response:
                        log_debug("User enabled startup")
                        success, message = startup_manager.enable_startup()
                        log_debug(f"Startup registration: {message}")
                    else:
                        log_debug("User declined startup")

                    startup_manager.mark_startup_prompt_shown()
                except Exception as e:
                    log_debug(f"Error showing startup prompt: {e}")
                    startup_manager.mark_startup_prompt_shown()

            # Run session, returns True if should re-login, False if exit
            should_continue = run_agent_session(token, user_id, username, org_name)
            if not should_continue:
                log_debug("Exiting application")
                break

    except Exception as e:
        log_debug(f"FATAL ERROR in main: {e}")
        import traceback
        log_debug(traceback.format_exc())
        traceback.print_exc()
        log_debug("Debug log written to: data/debug.log")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
