from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """
    Identity extracted from a verified JWT. Deliberately NOT a DB read on
    every request - role/username come straight from the token claims
    django-service signed. See jwt_auth.issue_token_for_user on the
    Django side for why that's an acceptable tradeoff.
    """

    id: int
    username: str
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token. Obtain one from POST /accounts/api/token/ on the Django service.",
        )

    try:
        settings = get_settings()
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    return CurrentUser(id=payload["user_id"], username=payload["username"], role=payload["role"])


def require_role(*allowed_roles: str):
    """Dependency factory, mirroring apps.accounts.decorators.role_required on the Django side."""

    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this resource.")
        return user

    return _check


require_student = require_role("STUDENT")
require_admin = require_role("ADMIN")
require_any_role = require_role("STUDENT", "ADMIN")
