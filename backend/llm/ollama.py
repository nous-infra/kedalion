"""Ollama client – the only place in Kedalion that talks to the model.

Uses Ollama's native chat API (/api/chat) without streaming.
Every failure becomes LLMError, so callers never see transport details.
See docs/llm.md for an overview.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx2

CHAT_PATH = "/api/chat"
CONNECT_TIMEOUT_SECONDS = 5.0


class LLMError(Exception):
    """The model could not be reached or gave an unusable answer."""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._model = model
        self._http = httpx2.AsyncClient(
            base_url=base_url,
            timeout=httpx2.Timeout(timeout_seconds, connect=CONNECT_TIMEOUT_SECONDS),
            trust_env=False,  # ignore proxy variables – requests go to Ollama only
            follow_redirects=False,
            transport=transport,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMReply:
        """Send the conversation (and optional tools) and return the reply."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "think": False,
        }
        if tools:
            payload["tools"] = tools
        try:
            response = await self._http.post(CHAT_PATH, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx2.TimeoutException:
            raise LLMError("model timed out") from None
        except httpx2.HTTPStatusError as exc:
            # Status code only – the body could contain internal details
            raise LLMError(f"model returned HTTP {exc.response.status_code}") from None
        except (httpx2.HTTPError, ValueError):
            raise LLMError("model not reachable or invalid response") from None
        return _parse_reply(data)

    async def aclose(self) -> None:
        await self._http.aclose()


def _parse_reply(data: Any) -> LLMReply:
    """Check the answer format strictly; the model's output is data, not trusted."""
    message = data.get("message") if isinstance(data, dict) else None
    if not isinstance(message, dict):
        raise LLMError("invalid response format")
    content = message.get("content") or ""
    if not isinstance(content, str):
        raise LLMError("invalid response format")

    calls: list[ToolCall] = []
    for raw in message.get("tool_calls") or []:
        function = raw.get("function") if isinstance(raw, dict) else None
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            raise LLMError("invalid tool call format")
        arguments = function.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise LLMError("invalid tool call format")
        calls.append(ToolCall(name=function["name"], arguments=arguments))
    return LLMReply(content=content, tool_calls=calls)
