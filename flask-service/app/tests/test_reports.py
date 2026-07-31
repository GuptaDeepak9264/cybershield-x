import os

from app.models import ScanLog


def test_generate_report_creates_pdf_file(client, student_user, auth_headers, db_session, media_root):
    db_session.add(ScanLog(
        user_id=student_user.id, scan_type="URL", target="https://example.com",
        status="CLEAN", security_score=95, detail="Host: example.com",
    ))
    db_session.commit()

    response = client.post("/api/v1/reports/generate", headers=auth_headers(student_user))
    assert response.status_code == 201
    body = response.get_json()
    assert body["file"].startswith("reports/")
    assert body["file"].endswith(".pdf")

    absolute_path = os.path.join(media_root, body["file"])
    assert os.path.exists(absolute_path)
    assert os.path.getsize(absolute_path) > 0


def test_generate_report_with_no_scans_still_succeeds(client, student_user, auth_headers):
    response = client.post("/api/v1/reports/generate", headers=auth_headers(student_user))
    assert response.status_code == 201


def test_student_cannot_download_another_students_report(client, student_user, admin_user, auth_headers):
    gen = client.post("/api/v1/reports/generate", headers=auth_headers(admin_user))
    report_id = gen.get_json()["id"]

    response = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers(student_user))
    assert response.status_code == 403


def test_admin_can_download_any_report(client, student_user, admin_user, auth_headers):
    gen = client.post("/api/v1/reports/generate", headers=auth_headers(student_user))
    report_id = gen.get_json()["id"]

    response = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers(admin_user))
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
