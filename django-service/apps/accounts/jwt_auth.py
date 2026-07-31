from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings


def issue_token_for_user(user) -> dict:
    """
    Build the JWT payload for a given Django user.

    Kept deliberately thin: user_id, username, role, exp. FastAPI trusts
    `role` from the token rather than re-querying MySQL on every request -
    that's a conscious tradeoff (a role change won't take effect for an
    already-issued token until it expires) in exchange for not hitting the
    DB on every API call. JWT_EXPIRATION_MINUTES is the knob that controls
    how long that staleness window can be.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.JWT_EXPIRATION_MINUTES * 60}
