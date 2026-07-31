import hashlib
import io

from app.models import ThreatIntelEntry


def test_clean_text_file_scores_high(client, student_user, auth_headers):
    files = {"file": ("notes.txt", io.BytesIO(b"just some notes"), "text/plain")}
    response = client.post("/api/v1/scan/file", headers=auth_headers(student_user), files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CLEAN"
    assert body["security_score"] >= 70


def test_executable_extension_lowers_score(client, student_user, auth_headers):
    files = {"file": ("tool.exe", io.BytesIO(b"MZ fake exe bytes"), "application/octet-stream")}
    response = client.post("/api/v1/scan/file", headers=auth_headers(student_user), files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["security_score"] < 70


def test_known_malicious_hash_flagged(client, student_user, auth_headers, db_session):
    content = b"totally malicious content"
    file_hash = hashlib.sha256(content).hexdigest()
    db_session.add(ThreatIntelEntry(
        indicator=file_hash, indicator_type="FILE_HASH", severity="CRITICAL", description="Known trojan.",
        added_by_id=None,
    ))
    db_session.commit()

    files = {"file": ("payload.bin", io.BytesIO(content), "application/octet-stream")}
    response = client.post("/api/v1/scan/file", headers=auth_headers(student_user), files=files)
    body = response.json()
    assert body["status"] == "MALICIOUS"
    assert body["security_score"] <= 5


def test_https_url_scores_higher_than_raw_ip(client, student_user, auth_headers):
    good = client.post("/api/v1/scan/url", headers=auth_headers(student_user), json={"url": "https://example.com"})
    bad = client.post("/api/v1/scan/url", headers=auth_headers(student_user), json={"url": "http://192.168.1.1/login"})
    assert good.json()["security_score"] > bad.json()["security_score"]


def test_known_malicious_domain_flagged(client, student_user, auth_headers, db_session):
    db_session.add(ThreatIntelEntry(
        indicator="evil.example.com", indicator_type="DOMAIN", severity="HIGH", description="Phishing domain.",
        added_by_id=None,
    ))
    db_session.commit()

    response = client.post(
        "/api/v1/scan/url", headers=auth_headers(student_user), json={"url": "https://evil.example.com/login"}
    )
    assert response.json()["status"] == "MALICIOUS"


def test_student_only_sees_own_history(client, student_user, admin_user, auth_headers, db_session):
    client.post("/api/v1/scan/url", headers=auth_headers(student_user), json={"url": "https://a.example.com"})
    client.post("/api/v1/scan/url", headers=auth_headers(admin_user), json={"url": "https://b.example.com"})

    response = client.get("/api/v1/scan/history", headers=auth_headers(student_user))
    targets = [item["target"] for item in response.json()]
    assert "https://a.example.com" in targets
    assert "https://b.example.com" not in targets


def test_admin_sees_all_history(client, student_user, admin_user, auth_headers):
    client.post("/api/v1/scan/url", headers=auth_headers(student_user), json={"url": "https://a.example.com"})
    response = client.get("/api/v1/scan/history", headers=auth_headers(admin_user))
    targets = [item["target"] for item in response.json()]
    assert "https://a.example.com" in targets
