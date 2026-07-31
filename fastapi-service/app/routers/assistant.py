from fastapi import APIRouter, Depends

from ..schemas import AssistantChatRequest, AssistantChatResponse
from ..security import CurrentUser, require_any_role
from ..services.assistant import get_assistant_reply

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat(payload: AssistantChatRequest, user: CurrentUser = Depends(require_any_role)):
    reply, mode = get_assistant_reply(payload.message)
    return AssistantChatResponse(reply=reply, mode=mode)
