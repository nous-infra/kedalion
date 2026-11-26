"""Tests for the Ollama client, using a simulated Ollama (no network)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import httpx2
import pytest

from backend.llm.ollama import LLMError, LLMReply, OllamaClient, ToolCall

MESSAGES = [{"role": "user", "content": "Hello"}]
TOOLS = [{"type": "function", "function": {"name": "light_on", "parameters": {}}}]

Handler = Callable[[httpx2.Request], httpx2.Response]


def _ask(handler: Handler, tools: list[dict[str, Any]] | None = None) -> LLMReply:
    async def run() -> LLMReply:
        client = OllamaClient(
            "http://ollama.test:11434", "test-model", 5,
            transport=httpx2.MockTransport(handler),
        )
        try:
            return await client.chat(MESSAGES, tools)
        finally:
            await client.aclose()

    return asyncio.run(run())


def _answer(message: Any) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"message": message, "done": True})
    return handler


def _status(code: int, text: str) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(code, text=text)
    return handler


def _raise(exc_type: type[httpx2.HTTPError]) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise exc_type("simulated", request=request)
    return handler


def _recording(seen: dict[str, Any]) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx2.Response(200, json={"message": {"role": "assistant", "content": "Hi"}})
    return handler


def test_request_payload() -> None:
    seen: dict[str, Any] = {}
    _ask(_recording(seen))
    assert seen["path"] == "/api/chat"
    assert seen["body"] == {
        "model": "test-model", "messages": MESSAGES, "stream": False, "think": False,
    }


def test_tools_are_sent_when_given() -> None:
    seen: dict[str, Any] = {}
    _ask(_recording(seen), tools=TOOLS)
    assert seen["body"]["tools"] == TOOLS


def test_text_answer_is_parsed() -> None:
    reply = _ask(_answer({"role": "assistant", "content": "Hi there"}))
    assert reply == LLMReply(content="Hi there")


def test_tool_calls_are_parsed() -> None:
    reply = _ask(_answer({
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "light_on",
                                     "arguments": {"entity_id": "light.kitchen"}}}],
    }))
    assert reply.tool_calls == [ToolCall(name="light_on",
                                         arguments={"entity_id": "light.kitchen"})]


@pytest.mark.parametrize(
    ("handler", "message"),
    [
        (_status(500, "boom"), "HTTP 500"),
        (_raise(httpx2.ReadTimeout), "timed out"),
        (_raise(httpx2.ConnectError), "not reachable"),
        (_status(200, "not json"), "not reachable or invalid"),
        (_answer(None), "invalid response format"),
        (_answer({"content": 42}), "invalid response format"),
        (_answer({"content": "", "tool_calls": [{"function": {"arguments": {}}}]}),
         "invalid tool call"),
    ],
)
def test_failures_become_llm_error(handler: Handler, message: str) -> None:
    with pytest.raises(LLMError, match=message):
        _ask(handler)


def test_error_does_not_leak_response_body() -> None:
    with pytest.raises(LLMError) as exc:
        _ask(_status(500, "INTERNAL-DETAIL"))
    assert "INTERNAL-DETAIL" not in str(exc.value)
