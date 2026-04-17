"""
Discovery worker - periodic ONVIF camera re-scan.
"""

import threading
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscoveryWorker:
    """Periodically scans for new cameras and reports to backend."""

    def __init__(
        self,
        config_manager,
        log_emitter,
        interval_seconds: int = 600,
        wsdiscovery_timeout: int = 5
    ):
        """
        Initialize discovery worker.

        Args:
            config_manager: ConfigManager instance
            log_emitter: LogEmitter instance
            interval_seconds: Discovery interval (default 10 min)
            wsdiscovery_timeout: WS-Discovery timeout (seconds)
        """
        self.config_manager = config_manager
        self.log_emitter = log_emitter
        self.interval_seconds = interval_seconds
        self.wsdiscovery_timeout = wsdiscovery_timeout

        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        """Start the discovery thread."""
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("Started discovery worker")

    def stop(self):
        """Stop the discovery thread."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            logger.info("Stopped discovery worker")

    def _run(self):
        """Main discovery loop."""
        while not self.stop_event.is_set():
            self._discover_cameras()
            self.stop_event.wait(self.interval_seconds)

    def _discover_cameras(self):
        """Discover cameras via WS-Discovery."""
        try:
            logger.debug("Starting camera discovery...")
            self.log_emitter.emit("info", "discovery", "Scanning network for cameras...")

            # Import here to avoid issues if wsdiscovery not available
            from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
            from cctv_agent.core.onvif_client import ONVIFClient

            wsd = WSDiscovery()
            wsd.start()

            try:
                # Discover ONVIF devices
                services = wsd.searchServices(
                    types="dn:NetworkVideoTransmitter",
                    timeout=self.wsdiscovery_timeout
                )

                discovered = []
                for service in services:
                    try:
                        # Extract IP from XADDR
                        xaddr = service.getXAddrs()[0] if service.getXAddrs() else None
                        if not xaddr:
                            continue

                        # Parse IP from URL
                        from urllib.parse import urlparse
                        parsed = urlparse(xaddr)
                        ip = parsed.hostname

                        if ip:
                            discovered.append({
                                "ip": ip,
                                "xaddr": xaddr,
                                "scopes": service.getScopes()
                            })

                    except Exception as e:
                        logger.debug(f"Failed to process discovered service: {e}")

                if discovered:
                    logger.info(f"Discovered {len(discovered)} ONVIF devices")
                    self.log_emitter.emit(
                        "info",
                        "discovery",
                        f"Found {len(discovered)} cameras on network"
                    )

            finally:
                wsd.stop()

        except Exception as e:
            logger.warning(f"Discovery scan failed: {e}")
            self.log_emitter.emit(
                "warning",
                "discovery",
                f"Scan failed: {e}"
            )
