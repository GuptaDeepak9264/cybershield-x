import csv
import io

from app.models import ScanLog, ThreatIntelEntry


def _seed_scans(db_session, student_user, admin_user):
    db_session.add_all([
        ScanLog(user_id=student_user.id, scan_type="URL", target="https://a.com", status="CLEAN", security_score=90, detail=""),
        ScanLog(user_id=student_user.id, scan_type="URL", target="https://b.com", status="MALICIOUS", security_score=5, detail="matches a known threat intel entry"),
        ScanLog(user_id=admin_user.id, scan_type="FILE", target="tool.exe", status="SUSPICIOUS", security_score=55, detail="Executable file type"),
    ])
    db_session.commit()


def test_my_scans_csv_only_contains_own_rows(client, student_user, admin_user, auth_headers, db_session):
    _seed_scans(db_session, student_user, admin_user)
    response = client.get("/api/v1/export/my-scans.csv", headers=auth_headers(student_user))
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    targets = {row["target"] for row in rows}
    assert targets == {"https://a.com", "https://b.com"}


def test_all_scans_csv_requires_admin(client, student_user, auth_headers):
    response = client.get("/api/v1/export/scans.csv", headers=auth_headers(student_user))
    assert response.status_code == 403


def test_all_scans_csv_includes_username_column(client, student_user, admin_user, auth_headers, db_session):
    _seed_scans(db_session, student_user, admin_user)
    response = client.get("/api/v1/export/scans.csv", headers=auth_headers(admin_user))
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert "username" in rows[0]
    assert len(rows) == 3


def test_analytics_summary(client, student_user, admin_user, auth_headers, db_session):
    _seed_scans(db_session, student_user, admin_user)
    response = client.get("/api/v1/analytics/summary", headers=auth_headers(admin_user))
    body = response.get_json()
    assert body["total_scans"] == 3
    assert body["status_breakdown"]["MALICIOUS"] == 1


def test_keyword_frequency(client, student_user, admin_user, auth_headers, db_session):
    _seed_scans(db_session, student_user, admin_user)
    response = client.get("/api/v1/logs/keyword-frequency", headers=auth_headers(admin_user))
    body = response.get_json()
    assert body["matches a known threat intel entry"] == 1
    assert body["Executable file type"] == 1


def test_anomaly_detection_returns_shape(client, admin_user, auth_headers):
    response = client.get("/api/v1/logs/anomalies", headers=auth_headers(admin_user))
    assert response.status_code == 200
    body = response.get_json()
    assert "is_anomaly" in body
    assert "note" in body
