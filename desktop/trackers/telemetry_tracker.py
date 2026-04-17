import time
import psutil
from desktop.storage.logger import logger
from desktop.config import TELEMETRY_INTERVAL
from desktop.trackers.session_manager import get_session_manager

class TelemetryTracker:
    def run(self, stop_event, pause_event=None):
        print("Telemetry Tracker started.")
        while not stop_event.is_set():
            if pause_event and pause_event.is_set():
                time.sleep(1)
                continue

            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory()
                battery = psutil.sensors_battery()
                net = psutil.net_io_counters()

                data = {
                    "cpu_percent": cpu_percent,
                    "ram_percent": ram.percent,
                    "ram_used_gb": round(ram.used / (1024**3), 2),
                    "battery_percent": battery.percent if battery else None,
                    "battery_charging": battery.power_plugged if battery else None,
                    "network_sent_mb": round(net.bytes_sent / (1024**2), 2),
                    "network_recv_mb": round(net.bytes_recv / (1024**2), 2)
                }
                
                session_id = get_session_manager().get_session_id()
                logger.log_event("telemetry", data, session_id=session_id)
            except Exception as e:
                print(f"Error gathering telemetry: {e}")
            
            # Wait for interval
            for _ in range(TELEMETRY_INTERVAL):
                if stop_event.is_set():
                    break
                time.sleep(1)
