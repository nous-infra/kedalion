"""OpenAI-compatible chat endpoint – placeholder until the agent loop exists."""

import time
import uuid

from fastapi import APIRouter

from backend.api.auth import Channel

router = APIRouter(prefix="/v1")


@router.post("/chat/completions")
def chat_completions(channel: Channel) -> dict[str, object]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "kedalion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Kedalion online (channel: {channel})",
                },
                "finish_reason": "stop",
            }
        ],
    }
