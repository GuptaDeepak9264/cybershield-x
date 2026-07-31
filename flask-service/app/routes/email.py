from flask import Blueprint, current_app, g, jsonify, request

from .. import get_db
from ..auth import admin_required
from ..models import Notification, User
from ..services.email_service import send_email

email_bp = Blueprint("email", __name__, url_prefix="/api/v1/email")


@email_bp.post("/send")
@admin_required
def send_direct_email():
    """Admin-composed one-off email to a specific user, by user id."""
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id")
    subject = body.get("subject")
    message = body.get("message")

    if not all([user_id, subject, message]):
        return jsonify({"detail": "user_id, subject, and message are required."}), 400

    db = get_db()
    settings = current_app.config["SETTINGS"]
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        return jsonify({"detail": "User not found."}), 404

    mode = send_email(settings, target.email, subject, message)
    return jsonify({"sent_to": target.email, "mode": mode}), 200


@email_bp.post("/notify/<int:notification_id>")
@admin_required
def email_notification(notification_id: int):
    """
    Deliver an existing Django-created Notification by email. Handles both
    a targeted notification (one recipient) and a broadcast (recipient_id
    is null -> emails every active student). This is the Flask side of the
    "Email Notification Service" role from the brief; actually calling
    this automatically whenever Django creates a Notification is Milestone
    5's job (cross-service call/webhook), not this milestone's.
    """
    db = get_db()
    settings = current_app.config["SETTINGS"]

    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        return jsonify({"detail": "Notification not found."}), 404

    if notification.recipient_id is not None:
        recipients = db.query(User).filter(User.id == notification.recipient_id, User.is_active.is_(True)).all()
    else:
        recipients = db.query(User).filter(User.role == "STUDENT", User.is_active.is_(True)).all()

    results = []
    for recipient in recipients:
        mode = send_email(settings, recipient.email, notification.title, notification.message)
        results.append({"user": recipient.username, "email": recipient.email, "mode": mode})

    return jsonify({"notification_id": notification_id, "delivered_to": results, "count": len(results)}), 200
