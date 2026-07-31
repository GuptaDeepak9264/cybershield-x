from dataclasses import dataclass
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request


@dataclass
class CurrentUser:
    id: int
    username: str
    role: str


def _extract_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.removeprefix("Bearer ").strip()


def login_required(view_func):
    """Verifies the JWT and stashes a CurrentUser on flask.g.current_user."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"detail": "Missing bearer token."}), 401

        settings = current_app.config["SETTINGS"]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({"detail": "Token has expired."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"detail": "Invalid token."}), 401

        g.current_user = CurrentUser(id=payload["user_id"], username=payload["username"], role=payload["role"])
        return view_func(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles: str):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            if g.current_user.role not in allowed_roles:
                return jsonify({"detail": "You do not have access to this resource."}), 403
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


admin_required = role_required("ADMIN")
any_role_required = role_required("STUDENT", "ADMIN")
