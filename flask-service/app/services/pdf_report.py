import os
import tempfile
import uuid
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import Settings
from ..models import ScanLog
from .scoring import compute_security_score


def _render_pdf(username: str, scans: list[ScanLog], output_path: str) -> None:
    status_counts: dict[str, int] = {}
    for scan in scans:
        status_counts[scan.status] = status_counts.get(scan.status, 0) + 1
    score, explanation = compute_security_score(status_counts)

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    story = []

    story.append(Paragraph("CyberShield X - Security Summary Report", styles["Title"]))
    story.append(Paragraph(f"Generated for: {username}", styles["Normal"]))
    story.append(Paragraph(f"Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph(f"<b>Security Score: {score}/100</b>", styles["Heading2"]))
    story.append(Paragraph(explanation, styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Recent Scan Activity", styles["Heading2"]))
    table_data = [["Type", "Target", "Status", "Score", "Date"]]
    for scan in scans[:25]:
        table_data.append([
            scan.scan_type,
            (scan.target[:45] + "...") if len(scan.target) > 45 else scan.target,
            scan.status,
            str(scan.security_score) if scan.security_score is not None else "-",
            scan.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    table = Table(table_data, colWidths=[0.6 * inch, 2.8 * inch, 1 * inch, 0.6 * inch, 1.3 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e141b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
    ]))
    story.append(table)

    if not scans:
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("No scans on record yet.", styles["Normal"]))

    doc.build(story)


def build_security_report_pdf(username: str, scans: list[ScanLog], settings: Settings) -> str:
    """
    Builds a one-page PDF security summary. Returns a path RELATIVE to
    wherever it was stored (e.g. "reports/abc123.pdf") - that's what gets
    stored in Report.file, matching Django's FileField(upload_to="reports/")
    convention exactly, whether that file lives on local disk or in S3.
    """
    filename = f"{uuid.uuid4().hex}.pdf"
    relative_path = f"reports/{filename}"

    if settings.USE_S3:
        # Render to a throwaway temp file, upload it, then discard the
        # local copy - this service never needs to keep the PDF once
        # object storage has it, and Django's S3 storage backend will
        # read the exact same bucket/key.
        import boto3

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            _render_pdf(username, scans, tmp_path)
            client_kwargs = {
                "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                "region_name": settings.AWS_S3_REGION_NAME,
            }
            if settings.AWS_S3_ENDPOINT_URL:
                client_kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT_URL
            s3 = boto3.client("s3", **client_kwargs)
            s3.upload_file(tmp_path, settings.AWS_STORAGE_BUCKET_NAME, relative_path, ExtraArgs={"ContentType": "application/pdf"})
        finally:
            os.unlink(tmp_path)
    else:
        reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        absolute_path = os.path.join(reports_dir, filename)
        _render_pdf(username, scans, absolute_path)

    return relative_path
