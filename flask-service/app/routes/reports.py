import os

from flask import Blueprint, current_app, g, jsonify, redirect, send_from_directory

from .. import get_db
from ..auth import any_role_required
from ..models import Report, ScanLog, User
from ..services.pdf_report import build_security_report_pdf

reports_bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")


@reports_bp.post("/generate")
@any_role_required
def generate_report():
    db = get_db()
    settings = current_app.config["SETTINGS"]

    user = db.query(User).filter(User.id == g.current_user.id).first()
    if user is None:
        return jsonify({"detail": "User not found in database."}), 404

    scans = db.query(ScanLog).filter(ScanLog.user_id == user.id).order_by(ScanLog.created_at.desc()).all()
    relative_path = build_security_report_pdf(user.username, scans, settings)

    report = Report(
        user_id=user.id,
        title=f"Security Summary - {user.username}",
        file=relative_path,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return jsonify({
        "id": report.id,
        "title": report.title,
        "file": report.file,
        "created_at": report.created_at.isoformat(),
    }), 201


@reports_bp.get("/<int:report_id>/download")
@any_role_required
def download_report(report_id: int):
    db = get_db()
    settings = current_app.config["SETTINGS"]

    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        return jsonify({"detail": "Report not found."}), 404
    if g.current_user.role != "ADMIN" and report.user_id != g.current_user.id:
        return jsonify({"detail": "You do not have access to this report."}), 403
    if not report.file:
        return jsonify({"detail": "This report has no generated file."}), 404

    if settings.USE_S3:
        import boto3

        client_kwargs = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_S3_REGION_NAME,
        }
        if settings.AWS_S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT_URL
        s3 = boto3.client("s3", **client_kwargs)
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": report.file},
            ExpiresIn=300,
        )
        return redirect(url)

    directory = os.path.join(settings.MEDIA_ROOT, os.path.dirname(report.file))
    filename = os.path.basename(report.file)
    return send_from_directory(directory, filename, as_attachment=True, download_name=f"{report.title}.pdf")
