from fastapi import APIRouter, Depends

from ..schemas import PasswordCheckRequest, PasswordCheckResponse
from ..security import CurrentUser, require_any_role
from ..services.password_strength import score_password

router = APIRouter(prefix="/api/v1/password", tags=["password"])


@router.post("/check", response_model=PasswordCheckResponse)
def check_password(payload: PasswordCheckRequest, user: CurrentUser = Depends(require_any_role)):
    # payload.password never touches a log line, a DB row, or a response
    # field beyond the score/label/feedback derived from it.
    score, label, feedback = score_password(payload.password)
    return PasswordCheckResponse(score=score, label=label, feedback=feedback)
