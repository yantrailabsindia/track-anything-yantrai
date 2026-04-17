"""
Beautiful, user-friendly ProMe Dashboard Window with tabs.
Displays real-time tracking metrics and system status.
Runs as a standalone process — tkinter needs the main thread on Windows.
"""
import tkinter as tk
from tkinter import ttk
import psutil
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from desktop.config import DATA_DIR, LOGS_DIR


BG_DARK = "#0f172a"
BG_CARD = "#1e293b"
BG_LOG = "#0b1120"
TEXT_PRIMARY = "#e2e8f0"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
ACCENT_BLUE = "#60a5fa"
ACCENT_GREEN = "#10b981"
ACCENT_PURPLE = "#a855f7"
TAB_ACTIVE = "#4f46e5"
TAB_INACTIVE = "#1e293b"


class DashboardWindow:
    def __init__(self, username: str, org_name: str):
        self.username = username
        self.org_name = org_name or "Personal"
        self.process = psutil.Process(os.getpid())
        self.window = None
        self.is_running = False
        self.current_tab = "dashboard"

        # Data for display (read from log files)
        self.keystrokes_live = 0
        self.clicks_live = 0
        self.keystrokes_today = 0
        self.clicks_today = 0
        self.window_sessions = 0
        self.active_window = "Idle"
        self.data_dir = DATA_DIR
        self.logs_dir = LOGS_DIR
        self.live_feed_file = DATA_DIR / "live_feed.json"
        self.all_entries = []
        self.live_events = []

    def load_daily_totals(self):
        """Load today's totals from log file."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.logs_dir / f"{today}.json"
            if not log_file.exists():
                return

            with open(log_file, "r") as f:
                entries = json.load(f)

            if not entries:
                return

            total_keys = 0
            total_clicks = 0
            sessions = 0
            last_window = ""
            last_keys = 0
            last_clicks = 0

            for entry in entries:
                event_type = entry.get("event_type", "")
                data = entry.get("data", {})

                if event_type == "input_summary":
                    total_keys += data.get("keystrokes", 0)
                    total_clicks += data.get("mouse_clicks", 0)
                    last_keys = data.get("keystrokes", 0)
                    last_clicks = data.get("mouse_clicks", 0)
                elif event_type == "window_change":
                    sessions += 1
                    last_window = data.get("window_title", "")

            self.keystrokes_today = total_keys
            self.clicks_today = total_clicks
            self.keystrokes_live = last_keys
            self.clicks_live = last_clicks
            self.window_sessions = sessions
            if last_window:
                self.active_window = last_window

            self.all_entries = entries

        except Exception as e:
            print(f"Error loading totals: {e}")

    def load_live_feed(self):
        """Load real-time events from the live feed file."""
        try:
            if self.live_feed_file.exists():
                with open(self.live_feed_file, "r") as f:
                    self.live_events = json.load(f)
            else:
                self.live_events = []
        except Exception:
            self.live_events = []

    def get_log_lines(self, max_entries=50):
        """Get formatted log lines for the logs tab."""
        if not self.all_entries:
            return ["  Waiting for activity...", "  Start using your computer and logs will appear here."]

        lines = []
        for entry in reversed(self.all_entries[-max_entries:]):
            event_type = entry.get("event_type", "unknown")
            timestamp = entry.get("timestamp", "")
            data = entry.get("data", {})

            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = "??:??:??"
            else:
                time_str = "??:??:??"

            if event_type == "input_summary":
                keys = data.get("keystrokes", 0)
                clicks = data.get("mouse_clicks", 0)
                dist = data.get("mouse_distance_px", 0)
                lines.append(f"  [{time_str}]  Keyboard: {keys} keys  |  Mouse: {clicks} clicks  |  {int(dist)}px moved")
            elif event_type == "window_change":
                window = data.get("window_title", "Unknown")[:50]
                dur = data.get("duration_seconds", 0)
                lines.append(f"  [{time_str}]  Window: {window}  ({dur}s)")
            elif event_type == "screenshot":
                lines.append(f"  [{time_str}]  Screenshot captured")
            elif event_type == "telemetry":
                cpu = data.get("cpu_percent", 0)
                ram = data.get("ram_percent", 0)
                lines.append(f"  [{time_str}]  System: CPU {cpu}%  RAM {ram}%")
            else:
                lines.append(f"  [{time_str}]  {event_type}")

        return lines if lines else ["  No recent activity"]

    def create_window(self):
        """Create and configure the dashboard window."""
        self.window = tk.Tk()
        self.window.title("ProMe Agent Dashboard")
        self.window.geometry("640x860")
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-toolwindow", True)  # Hide from taskbar
        self.window.configure(bg=BG_DARK)

        # Style
        style = ttk.Style()
        style.theme_use("clam")

        # ── Tab bar ──
        tab_bar = tk.Frame(self.window, bg=BG_DARK)
        tab_bar.pack(fill=tk.X, padx=16, pady=(12, 0))

        self.tab_dashboard_btn = tk.Button(
            tab_bar, text="Dashboard", font=("Segoe UI", 11, "bold"),
            bg=TAB_ACTIVE, fg="white", relief="flat", padx=24, pady=8,
            cursor="hand2", activebackground=TAB_ACTIVE, activeforeground="white",
            command=lambda: self.switch_tab("dashboard"))
        self.tab_dashboard_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.tab_logs_btn = tk.Button(
            tab_bar, text="Activity Logs", font=("Segoe UI", 11, "bold"),
            bg=TAB_INACTIVE, fg=TEXT_MUTED, relief="flat", padx=24, pady=8,
            cursor="hand2", activebackground=TAB_ACTIVE, activeforeground="white",
            command=lambda: self.switch_tab("logs"))
        self.tab_logs_btn.pack(side=tk.LEFT, padx=(0, 4))

        # ── Tab content frames ──
        self.tab_container = tk.Frame(self.window, bg=BG_DARK)
        self.tab_container.pack(fill=tk.BOTH, expand=True)

        # Dashboard tab
        self.dashboard_frame = tk.Frame(self.tab_container, bg=BG_DARK)
        self._build_dashboard_tab(self.dashboard_frame)

        # Logs tab
        self.logs_frame = tk.Frame(self.tab_container, bg=BG_DARK)
        self._build_logs_tab(self.logs_frame)

        # Show dashboard by default
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def switch_tab(self, tab_name):
        """Switch between dashboard and logs tabs."""
        self.current_tab = tab_name

        # Hide all
        self.dashboard_frame.pack_forget()
        self.logs_frame.pack_forget()

        if tab_name == "dashboard":
            self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
            self.tab_dashboard_btn.config(bg=TAB_ACTIVE, fg="white")
            self.tab_logs_btn.config(bg=TAB_INACTIVE, fg=TEXT_MUTED)
        else:
            self.logs_frame.pack(fill=tk.BOTH, expand=True)
            self.tab_logs_btn.config(bg=TAB_ACTIVE, fg="white")
            self.tab_dashboard_btn.config(bg=TAB_INACTIVE, fg=TEXT_MUTED)

    # ── Dashboard Tab ──

    def _build_dashboard_tab(self, parent):
        """Build all dashboard cards inside a scrollable frame."""
        canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview,
                                 bg=BG_CARD, troughcolor=BG_DARK)
        scroll_frame = tk.Frame(canvas, bg=BG_DARK)
        self.dash_scroll_frame = scroll_frame

        scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=620)
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Header
        header = tk.Frame(scroll_frame, bg=BG_DARK)
        header.pack(fill=tk.X, padx=20, pady=(12, 8))
        tk.Label(header, text="ProMe Dashboard", font=("Segoe UI", 20, "bold"),
                 bg=BG_DARK, fg=ACCENT_BLUE).pack(anchor="w")
        tk.Label(header, text=datetime.now().strftime("%A, %B %d, %Y"),
                 font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w")

        # Account card
        c = self._make_card(scroll_frame, "Account")
        tk.Label(c, text=f"User: {self.username}", font=("Segoe UI", 10),
                 bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="w", pady=2)
        tk.Label(c, text=f"Org: {self.org_name}", font=("Segoe UI", 10),
                 bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="w", pady=2)
        self.sync_label = tk.Label(c, text="Synced", font=("Segoe UI", 9),
                                   bg=BG_CARD, fg=ACCENT_GREEN)
        self.sync_label.pack(anchor="w", pady=2)

        # Startup toggle
        startup_frame = tk.Frame(c, bg=BG_CARD)
        startup_frame.pack(anchor="w", pady=8, fill=tk.X)
        tk.Label(startup_frame, text="Start on Windows Boot:", font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", side=tk.LEFT, padx=(0, 8))
        self.startup_toggle_btn = tk.Button(
            startup_frame, text="Enable", font=("Segoe UI", 9, "bold"),
            bg=BG_CARD, fg=TEXT_MUTED, relief="flat", padx=12, pady=2,
            cursor="hand2", activebackground=BG_CARD,
            command=self._toggle_startup
        )
        self.startup_toggle_btn.pack(anchor="w", side=tk.LEFT)
        self._update_startup_button()

        # Live Tracking card
        c = self._make_card(scroll_frame, "Live Tracking")
        tk.Label(c, text="Current Window:", font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", pady=(4, 0))
        self.window_label = tk.Label(c, text="Idle", font=("Segoe UI", 10),
                                     bg=BG_CARD, fg=ACCENT_PURPLE, wraplength=550, justify="left")
        self.window_label.pack(anchor="w", padx=8, pady=(0, 8))
        metrics = tk.Frame(c, bg=BG_CARD)
        metrics.pack(fill=tk.X, pady=4)
        self.keystroke_value = self._metric_widget(metrics, "Keystrokes (interval)", "0")
        self.click_value = self._metric_widget(metrics, "Clicks (interval)", "0")

        # Today's Activity card
        c = self._make_card(scroll_frame, "Today's Activity")
        metrics = tk.Frame(c, bg=BG_CARD)
        metrics.pack(fill=tk.X, pady=4)
        self.session_value = self._metric_widget(metrics, "Sessions", "0")
        self.total_keystroke_value = self._metric_widget(metrics, "Total Keys", "0")
        self.total_click_value = self._metric_widget(metrics, "Total Clicks", "0")

        # System Health card
        c = self._make_card(scroll_frame, "System Health")
        self.memory_label = tk.Label(c, text="Memory: -- MB", font=("Segoe UI", 9),
                                     bg=BG_CARD, fg=TEXT_SECONDARY)
        self.memory_label.pack(anchor="w", pady=2)
        self.cpu_label = tk.Label(c, text="CPU: --%", font=("Segoe UI", 9),
                                  bg=BG_CARD, fg=TEXT_SECONDARY)
        self.cpu_label.pack(anchor="w", pady=2)
        self.tracking_status_label = tk.Label(c, text="Status: Tracking Active",
                                              font=("Segoe UI", 10, "bold"),
                                              bg=BG_CARD, fg=ACCENT_GREEN)
        self.tracking_status_label.pack(anchor="w", pady=2)

        # Close button
        frame = tk.Frame(scroll_frame, bg=BG_DARK)
        frame.pack(fill=tk.X, padx=20, pady=(8, 16))
        tk.Button(frame, text="Close Dashboard", command=self.on_close,
                  bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=20, pady=8, cursor="hand2",
                  activebackground="#dc2626", activeforeground="white").pack(anchor="w")

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ── Logs Tab ──

    def _build_logs_tab(self, parent):
        """Build the full-screen logs tab."""
        # Header
        header = tk.Frame(parent, bg=BG_DARK)
        header.pack(fill=tk.X, padx=20, pady=(12, 8))
        tk.Label(header, text="Real-Time Activity Logs", font=("Segoe UI", 16, "bold"),
                 bg=BG_DARK, fg=ACCENT_BLUE).pack(side=tk.LEFT)

        self.log_count_label = tk.Label(header, text="0 events today",
                                         font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_MUTED)
        self.log_count_label.pack(side=tk.RIGHT)

        # Filter buttons
        filter_bar = tk.Frame(parent, bg=BG_DARK)
        filter_bar.pack(fill=tk.X, padx=20, pady=(0, 8))

        self.log_filter = "all"
        filters = [("All", "all"), ("Keystrokes & Clicks", "input_summary"), ("Windows", "window_change")]
        self.filter_buttons = {}
        for label, ftype in filters:
            btn = tk.Button(filter_bar, text=label, font=("Segoe UI", 9),
                            bg=TAB_ACTIVE if ftype == "all" else BG_CARD,
                            fg="white" if ftype == "all" else TEXT_MUTED,
                            relief="flat", padx=12, pady=4, cursor="hand2",
                            command=lambda f=ftype: self._set_log_filter(f))
            btn.pack(side=tk.LEFT, padx=2)
            self.filter_buttons[ftype] = btn

        # Log text area
        log_frame = tk.Frame(parent, bg=BG_LOG)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.logs_text = tk.Text(
            log_frame, bg=BG_LOG, fg="#a5d6a7",
            font=("Consolas", 9), relief="flat", borderwidth=0,
            wrap="word", padx=12, pady=12,
            insertbackground="#a5d6a7",
            yscrollcommand=scrollbar.set,
        )
        self.logs_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.logs_text.yview)

        self.logs_text.insert("1.0", "  Waiting for activity logs...")
        self.logs_text.config(state=tk.DISABLED)

    def _set_log_filter(self, filter_type):
        """Set the log filter and update display."""
        self.log_filter = filter_type
        for ftype, btn in self.filter_buttons.items():
            if ftype == filter_type:
                btn.config(bg=TAB_ACTIVE, fg="white")
            else:
                btn.config(bg=BG_CARD, fg=TEXT_MUTED)
        self._update_logs_display()

    def _update_startup_button(self):
        """Update startup button text and colors based on current status."""
        try:
            from desktop import startup_manager
            if startup_manager.is_startup_enabled():
                self.startup_toggle_btn.config(text="✓ Enabled", fg=ACCENT_GREEN)
            else:
                self.startup_toggle_btn.config(text="Enable", fg=TEXT_MUTED)
        except Exception as e:
            print(f"Error checking startup status: {e}")

    def _toggle_startup(self):
        """Toggle startup registration on/off."""
        try:
            from desktop import startup_manager
            from tkinter import messagebox

            if startup_manager.is_startup_enabled():
                # Disable startup
                success, message = startup_manager.disable_startup()
                if success:
                    messagebox.showinfo("Success", "ProMe startup has been disabled.\n\nYou will need to manually start ProMe after reboot.")
                    self._update_startup_button()
                else:
                    messagebox.showerror("Error", f"Failed to disable startup:\n{message}")
            else:
                # Enable startup
                success, message = startup_manager.enable_startup()
                if success:
                    messagebox.showinfo("Success", "ProMe will now start automatically on Windows startup.")
                    self._update_startup_button()
                else:
                    messagebox.showerror("Error", f"Failed to enable startup:\n{message}")
        except Exception as e:
            print(f"Error toggling startup: {e}")
            from tkinter import messagebox
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    # ── Shared Helpers ──

    def _make_card(self, parent, title=""):
        """Create a styled card frame and return the content frame."""
        outer = tk.Frame(parent, bg=BG_DARK)
        outer.pack(fill=tk.X, padx=16, pady=6)

        card = tk.Frame(outer, bg=BG_CARD, highlightbackground="#334155",
                        highlightthickness=1)
        card.pack(fill=tk.X)

        if title:
            tk.Label(card, text=title, font=("Segoe UI", 12, "bold"),
                     bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(12, 4))

        content = tk.Frame(card, bg=BG_CARD)
        content.pack(fill=tk.X, padx=16, pady=(4, 12))
        return content

    def _metric_widget(self, parent, label, initial_value):
        """Create a metric display widget, returns the value label."""
        box = tk.Frame(parent, bg=BG_CARD)
        box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        tk.Label(box, text=label, font=("Segoe UI", 9),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")
        val = tk.Label(box, text=initial_value, font=("Segoe UI", 22, "bold"),
                       bg=BG_CARD, fg=ACCENT_GREEN)
        val.pack(anchor="w", pady=(2, 0))
        return val

    # ── Update Loop ──

    def _update_logs_display(self):
        """Update the logs text widget based on live feed events."""
        if not self.live_events:
            text = "  Waiting for activity...\n  Every keystroke and click will appear here in real-time."
        else:
            # Apply filter
            if self.log_filter == "all":
                filtered = self.live_events
            elif self.log_filter == "input_summary":
                # Show keystrokes and clicks
                filtered = [e for e in self.live_events if e.get("event_type") in ("keystroke", "mouse_click")]
            elif self.log_filter == "window_change":
                filtered = [e for e in self.live_events if e.get("event_type") == "window_change"]
            else:
                filtered = [e for e in self.live_events if e.get("event_type") == self.log_filter]

            lines = []
            for entry in reversed(filtered[-100:]):
                event_type = entry.get("event_type", "unknown")
                timestamp = entry.get("timestamp", "")
                data = entry.get("data", {})

                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
                except Exception:
                    time_str = "??:??:??.???"

                if event_type == "keystroke":
                    lines.append(f"  [{time_str}]  KEY PRESS")
                elif event_type == "mouse_click":
                    btn = data.get("button", "?")
                    x = data.get("x", 0)
                    y = data.get("y", 0)
                    lines.append(f"  [{time_str}]  MOUSE CLICK  {btn}  ({x}, {y})")
                elif event_type == "window_change":
                    old_win = data.get("window_title", "")[:40]
                    new_win = data.get("new_window", "")[:40]
                    dur = data.get("duration_seconds", 0)
                    lines.append(f"  [{time_str}]  WINDOW  {old_win}  ->  {new_win}  ({dur}s)")
                elif event_type == "screenshot":
                    lines.append(f"  [{time_str}]  SCREENSHOT captured")
                elif event_type == "telemetry":
                    cpu = data.get("cpu_percent", 0)
                    ram = data.get("ram_percent", 0)
                    lines.append(f"  [{time_str}]  SYSTEM  CPU {cpu}%  RAM {ram}%")
                else:
                    lines.append(f"  [{time_str}]  {event_type.upper()}")

            text = "\n".join(lines) if lines else "  No matching events"

        try:
            self.logs_text.config(state=tk.NORMAL)
            self.logs_text.delete("1.0", tk.END)
            self.logs_text.insert("1.0", text)
            self.logs_text.config(state=tk.DISABLED)
        except Exception:
            pass

    def update_display(self):
        """Update dashboard with latest data."""
        if not self.window or not self.is_running:
            return

        self.load_daily_totals()
        self.load_live_feed()

        # Update dashboard tab widgets
        try:
            self.window_label.config(text=self.active_window[:60] if self.active_window else "Idle")
            self.keystroke_value.config(text=str(self.keystrokes_live))
            self.click_value.config(text=str(self.clicks_live))
            self.session_value.config(text=str(self.window_sessions))
            self.total_keystroke_value.config(text=f"{self.keystrokes_today:,}")
            self.total_click_value.config(text=f"{self.clicks_today:,}")
        except Exception:
            pass

        # System health
        try:
            mem = self.process.memory_info()
            mb = mem.rss / (1024 * 1024)
            pct = self.process.memory_percent()
            self.memory_label.config(text=f"Memory: {mb:.0f} MB ({pct:.1f}%)")
            cpu = self.process.cpu_percent(interval=0.1)
            self.cpu_label.config(text=f"CPU: {cpu:.1f}%")
        except Exception:
            pass

        # Update logs tab
        self.log_count_label.config(text=f"{len(self.live_events)} live events")
        self._update_logs_display()

        if self.window and self.is_running:
            self.window.after(2000, self.update_display)

    def on_close(self):
        """Handle window close."""
        self.is_running = False
        if self.window:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None

    def run(self):
        """Create window and run mainloop (blocking)."""
        self.load_daily_totals()
        self.create_window()
        self.is_running = True
        self.update_display()
        self.window.mainloop()


def main():
    """Entry point when run as standalone dashboard process."""
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


if __name__ == "__main__":
    main()
