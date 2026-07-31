def test_missing_token_rejected(client):
    response = client.get("/api/v1/scan/history")
    assert response.status_code == 401


def test_invalid_token_rejected(client):
    response = client.get("/api/v1/scan/history", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_valid_token_accepted(client, student_user, auth_headers):
    response = client.get("/api/v1/scan/history", headers=auth_headers(student_user))
    assert response.status_code == 200
    assert response.json() == []
