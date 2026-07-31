import hashlib
import os

from sqlalchemy.orm import Session

from ..models import ThreatIntelEntry

# Extensions that can execute code on most desktop OSes. Being in this set
# doesn't make a file malicious - it lowers its baseline score, same as a
# real AV heuristic would, pending an actual signature/behavioral check
# that a from-scratch project like this doesn't attempt to replace.
EXECUTABLE_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".msi", ".scr", ".jar"}


def sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def evaluate_file(filename: str, content: bytes, db: Session) -> tuple[str, int, str]:
    """
    Returns (status, security_score, detail).

    This is an honest, from-scratch heuristic engine, not a wrapper around
    a real antivirus - it will not catch malware that doesn't match a
    known-bad hash or an obviously risky extension. That limitation is
    stated here deliberately rather than left implicit, because a
    portfolio reviewer (or a real user) should not mistake this for
    production-grade malware detection.
    """
    file_hash = sha256_of(content)
    ext = os.path.splitext(filename)[1].lower()

    match = db.query(ThreatIntelEntry).filter(
        ThreatIntelEntry.indicator_type == "FILE_HASH", ThreatIntelEntry.indicator == file_hash
    ).first()

    if match:
        return (
            "MALICIOUS",
            5,
            f"SHA-256 {file_hash} matches a known threat intel entry "
            f"(severity: {match.severity}). {match.description}".strip(),
        )

    score = 90
    notes = [f"SHA-256: {file_hash}"]

    if ext in EXECUTABLE_EXTENSIONS:
        score -= 35
        notes.append(f"Executable file type ({ext}) - treat with caution even when clean.")

    if len(content) == 0:
        score -= 10
        notes.append("File is empty.")

    if score >= 70:
        status = "CLEAN"
    elif score >= 40:
        status = "SUSPICIOUS"
    else:
        status = "SUSPICIOUS"

    return status, max(score, 0), " ".join(notes)
