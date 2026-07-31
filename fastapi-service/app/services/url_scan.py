import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..models import ThreatIntelEntry

IP_HOST_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
SUSPICIOUS_TLDS = {".zip", ".xyz", ".top", ".gq", ".tk"}


def evaluate_url(url: str, db: Session) -> tuple[str, int, str]:
    """
    Same honesty note as file_scan: this is pattern-based heuristics
    (known-bad domain lookup + a handful of red flags), not a live
    reputation service or sandboxed browser. It won't catch a
    freshly-registered phishing domain that isn't already in the threat
    database and doesn't trip a heuristic.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    notes = [f"Host: {host or 'unparseable'}"]

    for indicator_type in ("URL", "DOMAIN"):
        candidate = url if indicator_type == "URL" else host
        match = db.query(ThreatIntelEntry).filter(
            ThreatIntelEntry.indicator_type == indicator_type, ThreatIntelEntry.indicator == candidate
        ).first()
        if match:
            return (
                "MALICIOUS",
                5,
                f"Matches known threat intel entry (severity: {match.severity}). {match.description}".strip(),
            )

    score = 90

    if not parsed.scheme == "https":
        score -= 15
        notes.append("Not served over HTTPS.")

    if IP_HOST_PATTERN.match(host):
        score -= 25
        notes.append("Host is a raw IP address rather than a domain name - common in phishing links.")

    if host.count(".") >= 4:
        score -= 15
        notes.append("Unusually deep subdomain structure.")

    if any(host.endswith(tld) for tld in SUSPICIOUS_TLDS):
        score -= 15
        notes.append("Uses a TLD frequently abused for throwaway phishing domains.")

    if "@" in url:
        score -= 20
        notes.append("Contains an '@' before the host - a classic URL-obfuscation trick.")

    score = max(score, 0)
    if score >= 70:
        status = "CLEAN"
    else:
        status = "SUSPICIOUS"

    return status, score, " ".join(notes)
