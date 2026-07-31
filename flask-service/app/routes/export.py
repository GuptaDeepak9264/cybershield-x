from flask import Blueprint, Response, g

from .. import get_db
from ..auth import admin_required, any_role_required
from ..models import ScanLog, User
from ..services.csv_export import scans_to_csv, users_to_csv

export_bp = Blueprint("export", __name__, url_prefix="/api/v1/export")


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@export_bp.get("/my-scans.csv")
@any_role_required
def export_my_scans():
    db = get_db()
    scans = db.query(ScanLog).filter(ScanLog.user_id == g.current_user.id).order_by(ScanLog.created_at.desc()).all()
    return _csv_response(scans_to_csv(scans, include_username=False), "my_scans.csv")


@export_bp.get("/scans.csv")
@admin_required
def export_all_scans():
    db = get_db()
    scans = db.query(ScanLog).order_by(ScanLog.created_at.desc()).all()
    return _csv_response(scans_to_csv(scans, include_username=True), "all_scans.csv")


@export_bp.get("/users.csv")
@admin_required
def export_users():
    db = get_db()
    users = db.query(User).order_by(User.id).all()
    return _csv_response(users_to_csv(users), "users.csv")
