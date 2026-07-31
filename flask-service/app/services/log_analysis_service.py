from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import ScanLog

# These phrases come directly from the vocabulary fastapi-service's
# heuristics write into ScanLog.detail (see fastapi-service/app/services/
# file_scan.py and url_scan.py) - this analysis is only as good as that
# shared vocabulary staying consistent, which is worth knowing if either
# side changes its wording.
RISK_KEYWORDS = [
    "matches a known threat intel entry",
    "Executable file type",
    "raw IP address",
    "Unusually deep subdomain",
    "abused for throwaway phishing",
    "URL-obfuscation trick",
    "Not served over HTTPS",
]


def keyword_frequency(db: Session, limit: int = 500) -> dict[str, int]:
    logs = db.query(ScanLog.detail).order_by(ScanLog.created_at.desc()).limit(limit).all()
    counts = {keyword: 0 for keyword in RISK_KEYWORDS}
    for (detail,) in logs:
        for keyword in RISK_KEYWORDS:
            if keyword in (detail or ""):
                counts[keyword] += 1
    return counts


def detect_malicious_rate_anomaly(db: Session) -> dict:
    """
    Compares the malicious-scan rate in the last 24h against the daily
    average over the previous 7 days. Flags an anomaly if today's rate is
    more than 2x the baseline - a simple, explainable threshold, not a
    statistical model. Good enough to surface "something changed," not
    good enough to replace an analyst's judgment.
    """
    now = datetime.now(timezone.utc)
    last_24h_start = now - timedelta(hours=24)
    baseline_start = now - timedelta(days=8)

    recent = db.query(ScanLog).filter(ScanLog.created_at >= last_24h_start).all()
    recent_total = len(recent)
    recent_malicious = sum(1 for s in recent if s.status == "MALICIOUS")
    recent_rate = (recent_malicious / recent_total) if recent_total else 0.0

    baseline = db.query(ScanLog).filter(
        ScanLog.created_at >= baseline_start, ScanLog.created_at < last_24h_start
    ).all()
    baseline_total = len(baseline)
    baseline_malicious = sum(1 for s in baseline if s.status == "MALICIOUS")
    baseline_rate = (baseline_malicious / baseline_total) if baseline_total else 0.0

    is_anomaly = baseline_total >= 5 and recent_total >= 3 and recent_rate > (baseline_rate * 2) and recent_rate > 0.1

    return {
        "last_24h_total": recent_total,
        "last_24h_malicious": recent_malicious,
        "last_24h_malicious_rate": round(recent_rate, 3),
        "baseline_7day_malicious_rate": round(baseline_rate, 3),
        "is_anomaly": is_anomaly,
        "note": (
            "Anomaly requires: at least 5 baseline scans, at least 3 scans in the last 24h, "
            "a malicious rate over 2x baseline, and an absolute rate above 10%."
        ),
    }
