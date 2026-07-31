import os

from app.models import Notification


def test_admin_can_send_direct_email_console_mode(client, student_user, admin_user, auth_headers, app):
    response = client.post(
        "/api/v1/email/send",
        headers=auth_headers(admin_user),
        json={"user_id": student_user.id, "subject": "Hello", "message": "Test message body."},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["mode"] == "console"
    assert body["sent_to"] == student_user.email

    outbox_path = app.config["SETTINGS"].EMAIL_OUTBOX_PATH
    assert os.path.exists(outbox_path)
    with open(outbox_path) as f:
        content = f.read()
    assert "Test message body." in content
    assert student_user.email in content


def test_student_cannot_send_email(client, student_user, auth_headers):
    response = client.post(
        "/api/v1/email/send",
        headers=auth_headers(student_user),
        json={"user_id": student_user.id, "subject": "x", "message": "y"},
    )
    assert response.status_code == 403


def test_notify_broadcast_reaches_all_active_students(client, student_user, admin_user, auth_headers, db_session):
    from app.models import User
    other_student = User(id=3, username="student2", email="s2@example.com", role="STUDENT", is_active=True)
    inactive_student = User(id=4, username="student3", email="s3@example.com", role="STUDENT", is_active=False)
    db_session.add_all([other_student, inactive_student])

    notification = Notification(
        sender_id=admin_user.id, recipient_id=None, title="Maintenance", message="Downtime tonight.",
    )
    db_session.add(notification)
    db_session.commit()

    response = client.post(f"/api/v1/email/notify/{notification.id}", headers=auth_headers(admin_user))
    assert response.status_code == 200
    body = response.get_json()
    delivered_usernames = {entry["user"] for entry in body["delivered_to"]}
    assert "student1" in delivered_usernames
    assert "student2" in delivered_usernames
    assert "student3" not in delivered_usernames  # inactive - correctly excluded
