import pystray
from PIL import Image, ImageDraw
import webbrowser
import subprocess
import sys
import os
import threading
from desktop.config import APP_NAME, API_URL

def create_image():
    # Create a simple icon if png is missing
    width = 64
    height = 64
    color1 = "royalblue"
    color2 = "white"

    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle([width//4, height//4, width*3//4, height*3//4], fill=color2)
    return image

class TrayIcon:
    def __init__(self, stop_callback, pause_event=None, username=None, org_name=None, logout_callback=None):
        self.stop_callback = stop_callback
        self.pause_event = pause_event  # threading.Event — set = paused
        self.logout_callback = logout_callback  # callback when user confirms logout
        self.icon = None
        self.user_name = username or "User"
        self.org_name = org_name

        # Dashboard subprocess
        self.dashboard_proc = None
        self.dashboard_open = False

    def open_local_dashboard(self, icon=None, item=None):
        """Launch/close the dashboard as a separate process."""
        try:
            # Check if dashboard process is still running
            if self.dashboard_proc and self.dashboard_proc.poll() is None:
                # Dashboard is running, kill it
                self.dashboard_proc.terminate()
                self.dashboard_proc = None
                self.dashboard_open = False
            else:
                # Launch same exe with --dashboard flag
                cmd = [
                    sys.executable,
                    "--dashboard",
                    "--username", self.user_name,
                    "--org", self.org_name or "Personal"
                ]

                self.dashboard_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.dashboard_open = True

            self._update_menu()
        except Exception as e:
            print(f"Error in open_local_dashboard: {e}")
            import traceback
            traceback.print_exc()

    def open_webapp_dashboard(self):
        """Open web dashboard in browser."""
        webbrowser.open("http://localhost:3000/dashboard")

    def toggle_sharing(self, icon, item):
        if self.pause_event:
            if self.pause_event.is_set():
                self.pause_event.clear()
            else:
                self.pause_event.set()
            self._update_menu()

    def handle_logout(self, icon, item):
        """Show logout confirmation dialog in a separate thread.

        pystray callbacks run inside the Windows message pump, so any
        blocking dialog (even native MessageBoxW) freezes. Spawning a
        new thread gives the dialog its own message loop.
        """
        def _logout_thread():
            try:
                from desktop.ui.logout_dialog import require_logout_confirmation
                if require_logout_confirmation(self.user_name):
                    # User confirmed logout
                    if self.logout_callback:
                        self.logout_callback()
                    # Stop the tray icon to exit the blocking run() call
                    if self.icon:
                        self.icon.stop()
            except Exception as e:
                print(f"Error in handle_logout: {e}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=_logout_thread, daemon=True).start()

    def _get_status_label(self):
        user_info = f"👤 {self.user_name}"
        mode = f"🏢 {self.org_name}" if self.org_name else user_info
        return mode

    def _get_sharing_label(self):
        if self.pause_event and self.pause_event.is_set():
            return "❌ Sharing Paused (Private)"
        return "✅ Sharing Enabled (Live)"

    def _get_dashboard_label(self):
        # Check if process is still alive
        if self.dashboard_proc and self.dashboard_proc.poll() is None:
            self.dashboard_open = True
            return "📊 Close Dashboard"
        else:
            self.dashboard_open = False
            return "📊 Open Dashboard"

    def _update_menu(self):
        if self.icon:
            self.icon.menu = pystray.Menu(
                pystray.MenuItem(self._get_status_label(), lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(self._get_dashboard_label(), self.open_local_dashboard),
                pystray.MenuItem("🌐 Open Web Dashboard", lambda i, item: self.open_webapp_dashboard()),
                pystray.MenuItem(self._get_sharing_label(), self.toggle_sharing),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(f"🚪 Log Out ({self.user_name})", self.handle_logout),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self.on_quit)
            )
            self.icon.update_menu()

    def run(self):
        image = create_image()
        self.icon = pystray.Icon(APP_NAME, image, APP_NAME)
        self._update_menu()
        print("Tray icon running with Privacy-First controls.")
        self.icon.run()

    def on_quit(self, icon, item):
        # Kill dashboard if running
        if self.dashboard_proc and self.dashboard_proc.poll() is None:
            self.dashboard_proc.terminate()
        self.icon.stop()
        self.stop_callback()
