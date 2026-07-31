from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import ScanLog


def summary(db: Session) -> dict:
    status_counts = dict(db.query(ScanLog.status, func.count(ScanLog.id)).group_by(ScanLog.status).all())
    type_counts = dict(db.query(ScanLog.scan_type, func.count(ScanLog.id)).group_by(ScanLog.scan_type).all())

    avg_score = db.query(func.avg(ScanLog.security_score)).filter(ScanLog.security_score.isnot(None)).scalar()

    return {
        "status_breakdown": status_counts,
        "type_breakdown": type_counts,
        "average_security_score": round(avg_score, 1) if avg_score is not None else None,
        "total_scans": sum(status_counts.values()),
    }


def daily_trend(db: Session, days: int = 7) -> list[dict]:
    """
    Scan volume per day for the last `days` days, oldest first. Computed
    in Python rather than a DB-specific date-bucketing function so this
    works identically on SQLite (dev/test) and MySQL (production) without
    an engine-specific branch.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.query(ScanLog.created_at, ScanLog.status).filter(ScanLog.created_at >= since).all()

    buckets: dict[str, dict[str, int]] = {}
    for created_at, status in rows:
        day_key = created_at.strftime("%Y-%m-%d")
        buckets.setdefault(day_key, {"total": 0, "malicious": 0})
        buckets[day_key]["total"] += 1
        if status == "MALICIOUS":
            buckets[day_key]["malicious"] += 1

    return [{"date": day, **counts} for day, counts in sorted(buckets.items())]
