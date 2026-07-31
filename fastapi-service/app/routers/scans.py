from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ScanLog
from ..schemas import ScanLogOut, URLScanRequest
from ..security import CurrentUser, require_any_role
from ..services.file_scan import evaluate_file
from ..services.url_scan import evaluate_url

router = APIRouter(prefix="/api/v1/scan", tags=["scanning"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.post("/file", response_model=ScanLogOut)
async def scan_file(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 25 MB limit.")

    status_, score, detail = evaluate_file(file.filename, content, db)

    log = ScanLog(
        user_id=user.id,
        scan_type="FILE",
        target=file.filename,
        status=status_,
        security_score=score,
        detail=detail,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/url", response_model=ScanLogOut)
def scan_url(
    payload: URLScanRequest,
    user: CurrentUser = Depends(require_any_role),
    db: Session = Depends(get_db),
):
    status_, score, detail = evaluate_url(payload.url, db)

    log = ScanLog(
        user_id=user.id,
        scan_type="URL",
        target=payload.url,
        status=status_,
        security_score=score,
        detail=detail,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/history", response_model=list[ScanLogOut])
def scan_history(
    user: CurrentUser = Depends(require_any_role),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    query = db.query(ScanLog).order_by(desc(ScanLog.created_at))
    # Students only ever see their own history; admins see everything -
    # same rule Django's admin_logs/history views enforce, kept consistent
    # across both surfaces on purpose.
    if user.role != "ADMIN":
        query = query.filter(ScanLog.user_id == user.id)
    return query.limit(min(limit, 100)).all()


@router.get("/{scan_id}", response_model=ScanLogOut)
def get_scan(scan_id: int, user: CurrentUser = Depends(require_any_role), db: Session = Depends(get_db)):
    log = db.query(ScanLog).filter(ScanLog.id == scan_id).first()
    if log is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if user.role != "ADMIN" and log.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this scan.")
    return log
