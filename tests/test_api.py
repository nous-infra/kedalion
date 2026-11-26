"""Tests for the API: health, token auth, channel detection and hardening."""

from __future__ import annotations

from types import MappingProxyType

import pytest
from fastapi.testclient import TestClient

from backend.api.tokens import token_digest
from backend.app import create_app
from backend.config import Config, Settings

KEY = b"k" * 32
TOKENS = {"voice": "voice-test-token", "chat": "chat-test-token"}


@pytest.fixture
def client() -> TestClient:
    config = Config(
        # model_construct skips env/.env loading – the real config is never read
        settings=Settings.model_construct(
            ollama_url="http://ollama.test:11434", ollama_model="test-model"
        ),
        hmac_key=KEY,
        channel_digests=MappingProxyType(
            {channel: token_digest(KEY, tok) for channel, tok in TOKENS.items()}
        ),
    )
    return TestClient(create_app(config))


def _chat(client: TestClient, headers: dict[str, str]):
    return client.post("/v1/chat/completions", headers=headers)


def _reply(response) -> str:
    return response.json()["choices"][0]["message"]["content"]


def test_health_needs_no_token(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("channel", ["voice", "chat"])
def test_channel_is_derived_from_token(client: TestClient, channel: str) -> None:
    response = _chat(client, {"Authorization": f"Bearer {TOKENS[channel]}"})
    assert response.status_code == 200
    assert _reply(response).endswith(f"(channel: {channel})")


def test_client_cannot_choose_channel(client: TestClient) -> None:
    headers = {"Authorization": f"Bearer {TOKENS['voice']}", "X-Channel": "chat"}
    assert _reply(_chat(client, headers)).endswith("(channel: voice)")


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong"},
        {"Authorization": "Bearer "},
        {"Authorization": f"Basic {TOKENS['voice']}"},
        {"Authorization": TOKENS["voice"]},
        {"Authorization": f"Bearer {TOKENS['voice']}x"},
    ],
)
def test_invalid_auth_is_rejected(client: TestClient, headers: dict[str, str]) -> None:
    response = _chat(client, headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_are_disabled(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404
