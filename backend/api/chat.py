"""OpenAI-compatible chat endpoint.

Placeholder until the agent loop exists: it validates the request and
replies with the detected channel and the number of messages it would use.
"""

from fastapi import APIRouter

from backend.api.auth import Channel
from backend.api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/v1")


@router.post("/chat/completions")
def chat_completions(body: ChatRequest, channel: Channel) -> ChatResponse:
    turns = body.conversation()
    return ChatResponse.from_text(
        f"Kedalion online (channel: {channel}, messages: {len(turns)})"
    )
