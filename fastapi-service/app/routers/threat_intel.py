from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ThreatIntelEntry
from ..schemas import ThreatIntelOut, ThreatLookupResponse
from ..security import CurrentUser, require_any_role

router = APIRouter(prefix="/api/v1/threat-intel", tags=["threat-intel"])

# Write access (create/edit/delete) intentionally lives only in Django's
# admin UI (apps.security.views.ThreatIntel*View) - it's low-volume,
# human-curated data with a review workflow attached to it, not a fit for
# an unauthenticated-adjacent high-throughput API. This router is
# deliberately read-only.


@router.get("/", response_model=list[ThreatIntelOut])
def list_threats(
    user: CurrentUser = Depends(require_any_role),
    db: Session = Depends(get_db),
    severity: str | None = None,
    limit: int = 50,
):
    query = db.query(ThreatIntelEntry)
    if severity:
        query = query.filter(ThreatIntelEntry.severity == severity.upper())
    return query.order_by(ThreatIntelEntry.created_at.desc()).limit(min(limit, 200)).all()


@router.get("/lookup", response_model=ThreatLookupResponse)
def lookup_indicator(
    indicator: str = Query(..., min_length=1),
    user: CurrentUser = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    """
    Check a raw indicator (URL, domain, IP, or file hash) against the
    threat database. If given a full URL, also checks its host as a
    DOMAIN indicator, since that's how scan_url's heuristics check things.
    """
    candidates = [indicator]
    parsed = urlparse(indicator)
    if parsed.hostname:
        candidates.append(parsed.hostname.lower())

    match = db.query(ThreatIntelEntry).filter(ThreatIntelEntry.indicator.in_(candidates)).first()
    if match:
        return ThreatLookupResponse(
            indicator=indicator, is_known_threat=True, severity=match.severity, description=match.description
        )
    return ThreatLookupResponse(indicator=indicator, is_known_threat=False)
