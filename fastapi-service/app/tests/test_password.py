def test_weak_common_password_scores_low(client, student_user, auth_headers):
    response = client.post(
        "/api/v1/password/check", headers=auth_headers(student_user), json={"password": "password"}
    )
    body = response.json()
    assert body["score"] <= 15
    assert body["label"] in ("Very Weak", "Weak")


def test_strong_password_scores_high(client, student_user, auth_headers):
    response = client.post(
        "/api/v1/password/check", headers=auth_headers(student_user), json={"password": "Xk9#mQ2!vLp8$zR4"}
    )
    body = response.json()
    assert body["score"] >= 90
    assert body["label"] in ("Strong", "Very Strong")


def test_password_never_echoed_back(client, student_user, auth_headers):
    response = client.post(
        "/api/v1/password/check", headers=auth_headers(student_user), json={"password": "MySecretPwd123!"}
    )
    assert "MySecretPwd123!" not in response.text
