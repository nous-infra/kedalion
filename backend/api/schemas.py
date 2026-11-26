"""Request and response models for the OpenAI-compatible chat endpoint.

Only the fields Kedalion needs are read; unknown fields are ignored.
See docs/api.md for the rules in plain words.
"""

from __future__ import annotations

import time
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

MAX_MESSAGES = 50
MAX_CONTENT_CHARS = 8000

# Roles Kedalion actually uses from the client's history
TRUSTED_ROLES = ("user", "assistant")


class ChatMessage(BaseModel):
    role: Literal["system", "developer", "user", "assistant", "tool"]
    # Plain text only; None is allowed because some clients send it
    content: Annotated[str, Field(max_length=MAX_CONTENT_CHARS)] | None = None


class ChatRequest(BaseModel):
    model: str = Field(default="kedalion", max_length=100)  # ignored
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)
    stream: Literal[False] = False  # streaming is not supported yet

    def conversation(self) -> list[ChatMessage]:
        """Return the messages Kedalion uses: user and assistant text only.

        System, developer and tool messages are dropped: the history comes
        from the client and cannot be trusted. Kedalion adds its own system
        prompt instead.
        """
        return [m for m in self.messages if m.role in TRUSTED_ROLES and m.content]

    @model_validator(mode="after")
    def _last_message_is_from_user(self) -> ChatRequest:
        turns = self.conversation()
        if not turns or turns[-1].role != "user":
            raise ValueError("the conversation must end with a user message")
        return self


class ResponseMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class Choice(BaseModel):
    index: int = 0
    message: ResponseMessage
    finish_reason: Literal["stop"] = "stop"


class ChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "kedalion"
    choices: list[Choice]

    @classmethod
    def from_text(cls, text: str) -> ChatResponse:
        """Build a complete response from a plain answer text."""
        return cls(choices=[Choice(message=ResponseMessage(content=text))])
