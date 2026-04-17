"""
Aggregator service — computes stats from the activity_logs SQL table.
Org-scoped: Queries are filtered by organization ID.
"""
from datetime import datetime, timedelta
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, join

from backend.models import ActivityLog, User


class Aggregator:
    @staticmethod
    def _build_date_query(db: Session, date_str: str, org_id: str = None, device_id: str = None, user_id: str = None, team_id: str = None):
        """Build a base query filtered by date/org/user/device/team. Returns (query, start, end) or None on bad date."""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)

        query = db.query(ActivityLog).filter(
            ActivityLog.timestamp >= start,
            ActivityLog.timestamp < end,
        )
        if org_id:
            query = query.filter(ActivityLog.org_id == org_id)
        if device_id:
            query = query.filter(ActivityLog.device_id == device_id)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if team_id:
            # Join with User table to filter by team membership
            query = query.join(User, ActivityLog.user_id == User.id).filter(User.team_id == team_id)

        return query, start, end

    @staticmethod
    def get_logs_for_date(db: Session, date_str: str, org_id: str = None, device_id: str = None, user_id: str = None, team_id: str = None, limit: int = 200, offset: int = 0):
        """Return log entries for a given date (YYYY-MM-DD), scoped by org/user/device/team, with pagination."""
        result = Aggregator._build_date_query(db, date_str, org_id=org_id, device_id=device_id, user_id=user_id, team_id=team_id)
        if result is None:
            return {"logs": [], "total": 0, "counts": {}}

        query, start, end = result

        # Get total count and per-type counts in a single query
        count_rows = (
            db.query(ActivityLog.event_type, func.count(ActivityLog.id))
            .filter(ActivityLog.timestamp >= start, ActivityLog.timestamp < end)
        )
        if org_id:
            count_rows = count_rows.filter(ActivityLog.org_id == org_id)
        if device_id:
            count_rows = count_rows.filter(ActivityLog.device_id == device_id)
        if user_id:
            count_rows = count_rows.filter(ActivityLog.user_id == user_id)
        if team_id:
            count_rows = count_rows.join(User, ActivityLog.user_id == User.id).filter(User.team_id == team_id)
        count_rows = count_rows.group_by(ActivityLog.event_type).all()

        counts = {etype: cnt for etype, cnt in count_rows}
        total = sum(counts.values())

        # Fetch paginated logs (most recent first)
        logs = query.order_by(ActivityLog.timestamp.desc()).offset(offset).limit(limit).all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "device_id": log.device_id,
                    "user_id": log.user_id,
                    "org_id": log.org_id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "event_type": log.event_type,
                    "data": log.data or {},
                }
                for log in logs
            ],
            "total": total,
            "counts": counts,
        }

    @staticmethod
    def get_logs_for_range(db: Session, start_date_str: str, end_date_str: str, org_id: str = None, device_id: str = None, user_id: str = None, team_id: str = None, limit: int = 500, offset: int = 0):
        """Return log entries across a date range (inclusive), with pagination and counts."""
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return {"logs": [], "total": 0, "counts": {}}

        start = datetime.combine(start_date, datetime.min.time())
        end = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

        query = db.query(ActivityLog).filter(
            ActivityLog.timestamp >= start,
            ActivityLog.timestamp < end,
        )
        count_query = db.query(ActivityLog.event_type, func.count(ActivityLog.id)).filter(
            ActivityLog.timestamp >= start,
            ActivityLog.timestamp < end,
        )
        if org_id:
            query = query.filter(ActivityLog.org_id == org_id)
            count_query = count_query.filter(ActivityLog.org_id == org_id)
        if device_id:
            query = query.filter(ActivityLog.device_id == device_id)
            count_query = count_query.filter(ActivityLog.device_id == device_id)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
            count_query = count_query.filter(ActivityLog.user_id == user_id)
        if team_id:
            query = query.join(User, ActivityLog.user_id == User.id).filter(User.team_id == team_id)
            count_query = count_query.join(User, ActivityLog.user_id == User.id).filter(User.team_id == team_id)

        count_rows = count_query.group_by(ActivityLog.event_type).all()
        counts = {etype: cnt for etype, cnt in count_rows}
        total = sum(counts.values())

        logs = query.order_by(ActivityLog.timestamp.desc()).offset(offset).limit(limit).all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "device_id": log.device_id,
                    "user_id": log.user_id,
                    "org_id": log.org_id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "event_type": log.event_type,
                    "data": log.data or {},
                }
                for log in logs
            ],
            "total": total,
            "counts": counts,
        }

    @staticmethod
    def compute_stats(db: Session, date_str: str, org_id: str = None, device_id: str = None, user_id: str = None, team_id: str = None):
        """Compute productivity stats for a given date, scoped by org/user/device/team.
        Uses a single DB query to fetch only window_change and input_summary events
        instead of loading every log into Python."""
        result = Aggregator._build_date_query(db, date_str, org_id=org_id, device_id=device_id, user_id=user_id, team_id=team_id)
        if result is None:
            return {"productivity_score": 0, "top_apps": [], "activity_summary": {"keystrokes": 0, "clicks": 0}, "total_time_seconds": 0}

        query, start, end = result

        # Only fetch the two event types we actually need for stats
        logs = (
            query
            .filter(ActivityLog.event_type.in_(["window_change", "input_summary"]))
            .all()
        )

        if not logs:
            return {"productivity_score": 0, "top_apps": [], "activity_summary": {"keystrokes": 0, "clicks": 0}, "total_time_seconds": 0}

        app_durations = Counter()
        total_keystrokes = 0
        total_clicks = 0
        total_time = 0

        for log in logs:
            data = log.data or {}

            if log.event_type == "window_change":
                app = data.get("window_title", "Unknown")
                if " - " in app:
                    app_name = app.split(" - ")[-1].strip()
                else:
                    app_name = app.strip()
                if len(app_name) > 35:
                    app_name = app_name[:32] + "..."
                if not app_name:
                    app_name = "Unknown"

                duration = data.get("duration_seconds", 0)
                app_durations[app_name] += duration
                total_time += duration

            elif log.event_type == "input_summary":
                total_keystrokes += data.get("keystrokes", 0)
                total_clicks += data.get("mouse_clicks", 0)

        active_minutes = total_time / 60 if total_time > 0 else 1
        raw_score = (total_keystrokes + total_clicks * 5) / active_minutes
        productivity_score = min(100, int(raw_score * 2))

        top_apps = [
            {"name": app, "duration": dur}
            for app, dur in app_durations.most_common(5)
        ]

        return {
            "productivity_score": productivity_score,
            "top_apps": top_apps,
            "activity_summary": {"keystrokes": total_keystrokes, "clicks": total_clicks},
            "total_time_seconds": total_time,
        }
