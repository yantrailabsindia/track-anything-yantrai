"""
Manages the capture schedule for the CCTV Agent.
Supports IST (Indian Standard Time) scheduling.
"""

import logging
from datetime import datetime, time
import pytz

logger = logging.getLogger(__name__)


class ScheduleManager:
    """Handles time-of-day scheduling for CCTV capture."""

    IST = pytz.timezone('Asia/Kolkata')

    def __init__(self, start_hour: int = 9, end_hour: int = 22):
        """
        Initialize with start and end hours in IST.
        Default: 9:00 AM to 10:00 PM IST.
        """
        self.start_time = time(start_hour, 0)
        self.end_time = time(end_hour, 0)
        logger.info(f"Schedule initialized: {self.start_time} to {self.end_time} IST")

    def is_currently_active(self) -> bool:
        """Check if current time is within the scheduled window in IST."""
        # Get current time in IST
        now_ist = datetime.now(self.IST).time()
        
        # Check if between start and end
        if self.start_time <= now_ist <= self.end_time:
            return True
            
        return False

    def get_ist_now(self) -> datetime:
        """Get current datetime in IST."""
        return datetime.now(self.IST)

    @staticmethod
    def ist_to_utc(ist_dt: datetime) -> datetime:
        """Convert IST datetime to UTC."""
        if ist_dt.tzinfo is None:
            ist_dt = ScheduleManager.IST.localize(ist_dt)
        return ist_dt.astimezone(pytz.UTC)
