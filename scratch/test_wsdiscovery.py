import sys
import logging
from pathlib import Path

# Add project root to sys.path
package_root = Path(__file__).resolve().parent.parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

try:
    from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery
    print("Successfully imported WSDiscovery")
    
    wsd = WSDiscovery()
    wsd.start()
    print("Started WSDiscovery")
    
    try:
        print("Searching for services (unfiltered, timeout 5s)...")
        services = wsd.searchServices(timeout=5)
        print(f"Found {len(services)} services")
        for s in services:
            print(f"  Service: {s.getXAddrs()}")
    finally:
        wsd.stop()
        print("Stopped WSDiscovery")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
