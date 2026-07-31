from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ScanLog
from ..schemas import SecurityScoreResponse
from ..security import CurrentUser, require_any_role

router = APIRouter(prefix="/api/v1/security-score", tags=["security-score"])


def _compute_score(user_id: int, db: Session) -> SecurityScoreResponse:
    counts = dict(
        db.query(ScanLog.status, func.count(ScanLog.id))
        .filter(ScanLog.user_id == user_id)
        .group_by(ScanLog.status)
        .all()
    )
    total = sum(counts.values())
    malicious = counts.get("MALICIOUS", 0)
    suspicious = counts.get("SUSPICIOUS", 0)
    clean = counts.get("CLEAN", 0)

    if total == 0:
        return SecurityScoreResponse(
            user_id=user_id,
            score=100,
            total_scans=0,
            malicious_count=0,
            suspicious_count=0,
            clean_count=0,
            explanation="No scans yet - starting score is neutral until you have activity to base it on.",
        )

    # Simple, explainable weighting: malicious hits hurt a lot more than
    # suspicious ones, clean scans don't add points beyond the baseline
    # (scanning safely is expected behavior, not a bonus). This is a
    # transparent formula, not a black-box ML score - deliberately so,
    # since a security score you can't explain to the user isn't useful
    # feedback.
    penalty = (malicious * 20) + (suspicious * 5)
    score = max(0, 100 - penalty)

    explanation = (
        f"{total} scan(s): {clean} clean, {suspicious} suspicious, {malicious} malicious. "
        f"Each malicious result costs 20 points, each suspicious result costs 5, floor of 0."
    )
    return SecurityScoreResponse(
        user_id=user_id,
        score=score,
        total_scans=total,
        malicious_count=malicious,
        suspicious_count=suspicious,
        clean_count=clean,
        explanation=explanation,
    )


@router.get("/me", response_model=SecurityScoreResponse)
def my_security_score(user: CurrentUser = Depends(require_any_role), db: Session = Depends(get_db)):
    return _compute_score(user.id, db)
