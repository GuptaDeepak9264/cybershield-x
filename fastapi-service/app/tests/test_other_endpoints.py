from app.models import ThreatIntelEntry


def test_threat_lookup_known_indicator(client, student_user, auth_headers, db_session):
    db_session.add(ThreatIntelEntry(
        indicator="bad.example.com", indicator_type="DOMAIN", severity="HIGH", description="Known bad.",
        added_by_id=None,
    ))
    db_session.commit()

    response = client.get(
        "/api/v1/threat-intel/lookup", headers=auth_headers(student_user), params={"indicator": "bad.example.com"}
    )
    body = response.json()
    assert body["is_known_threat"] is True
    assert body["severity"] == "HIGH"


def test_threat_lookup_unknown_indicator(client, student_user, auth_headers):
    response = client.get(
        "/api/v1/threat-intel/lookup", headers=auth_headers(student_user), params={"indicator": "totally-fine.com"}
    )
    assert response.json()["is_known_threat"] is False


def test_security_score_neutral_with_no_scans(client, student_user, auth_headers):
    response = client.get("/api/v1/security-score/me", headers=auth_headers(student_user))
    body = response.json()
    assert body["score"] == 100
    assert body["total_scans"] == 0


def test_security_score_drops_after_malicious_scan(client, student_user, auth_headers, db_session):
    db_session.add(ThreatIntelEntry(
        indicator="evil.example.com", indicator_type="DOMAIN", severity="CRITICAL", description="Bad.",
        added_by_id=None,
    ))
    db_session.commit()
    client.post("/api/v1/scan/url", headers=auth_headers(student_user), json={"url": "https://evil.example.com"})

    response = client.get("/api/v1/security-score/me", headers=auth_headers(student_user))
    body = response.json()
    assert body["score"] == 80  # 100 - 20 for one malicious hit
    assert body["malicious_count"] == 1


def test_assistant_fallback_mode_answers_known_topic(client, student_user, auth_headers):
    response = client.post(
        "/api/v1/assistant/chat", headers=auth_headers(student_user), json={"message": "how do I spot phishing?"}
    )
    body = response.json()
    assert body["mode"] == "fallback"
    assert "phishing" in body["reply"].lower() or "sender" in body["reply"].lower()


def test_assistant_fallback_default_reply_for_unknown_topic(client, student_user, auth_headers):
    response = client.post(
        "/api/v1/assistant/chat", headers=auth_headers(student_user), json={"message": "what's the weather today?"}
    )
    body = response.json()
    assert body["mode"] == "fallback"
    assert "fallback mode" in body["reply"].lower()
