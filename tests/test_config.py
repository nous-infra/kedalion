"""Tests for configuration loading and the fail-closed startup check."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from backend.config import ConfigError, load_config, load_config_or_exit

KEY_HEX = "ab" * 32
VOICE_DIGEST = "11" * 32
CHAT_DIGEST = "22" * 32


def _write(path: Path, content: str, mode: int = 0o600) -> None:
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


@pytest.fixture
def secrets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Valid setup in a temp dir; the real .env and secrets are never touched."""
    for name in list(os.environ):
        if name.startswith("KEDALION_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)  # no .env in cwd -> nothing loaded from the repo

    directory = tmp_path / "secrets"
    directory.mkdir()
    _write(directory / "hmac_key", KEY_HEX)
    _write(directory / "auth.json",
           json.dumps({"voice": VOICE_DIGEST, "chat": CHAT_DIGEST}))

    monkeypatch.setenv("KEDALION_OLLAMA_URL", "http://ollama.test:11434")
    monkeypatch.setenv("KEDALION_OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("KEDALION_SECRETS_DIR", str(directory))
    monkeypatch.setenv("KEDALION_AUTH_CONFIG_PATH", str(directory / "auth.json"))
    return directory


def test_valid_config_loads(secrets_dir: Path) -> None:
    config = load_config()
    assert config.hmac_key == bytes.fromhex(KEY_HEX)
    assert set(config.channel_digests) == {"voice", "chat"}


def test_repr_hides_secrets(secrets_dir: Path) -> None:
    text = repr(load_config())
    assert KEY_HEX not in text
    assert repr(bytes.fromhex(KEY_HEX)) not in text
    assert VOICE_DIGEST not in text


def test_missing_setting_is_named(secrets_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEDALION_OLLAMA_URL")
    with pytest.raises(ConfigError, match="ollama_url"):
        load_config()


def test_invalid_setting_value_is_not_echoed(
    secrets_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEDALION_OLLAMA_URL", "no-url-SENSITIVEVALUE")
    with pytest.raises(ConfigError) as exc:
        load_config()
    assert "SENSITIVEVALUE" not in str(exc.value)


def test_missing_key_file(secrets_dir: Path) -> None:
    (secrets_dir / "hmac_key").unlink()
    with pytest.raises(ConfigError, match="HMAC key not found"):
        load_config()


@pytest.mark.parametrize("mode", [0o644, 0o604, 0o602])
def test_key_accessible_by_others_is_rejected(secrets_dir: Path, mode: int) -> None:
    os.chmod(secrets_dir / "hmac_key", mode)
    with pytest.raises(ConfigError, match="accessible by other users"):
        load_config()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not-hex-at-all", "hex-encoded"),
        ("abc", "hex-encoded"),
        ("ab" * 16, "at least 32 bytes"),
    ],
)
def test_invalid_key_is_rejected(secrets_dir: Path, content: str, message: str) -> None:
    _write(secrets_dir / "hmac_key", content)
    with pytest.raises(ConfigError, match=message) as exc:
        load_config()
    assert content not in str(exc.value)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "not valid JSON"),
        ("[]", "exactly"),
        (json.dumps({"voice": VOICE_DIGEST}), "exactly"),
        (json.dumps({"voice": VOICE_DIGEST, "chat": CHAT_DIGEST, "admin": "33" * 32}),
         "exactly"),
        (json.dumps({"voice": "AB" * 32, "chat": CHAT_DIGEST}), "lowercase hex"),
        (json.dumps({"voice": "11" * 31, "chat": CHAT_DIGEST}), "lowercase hex"),
        (json.dumps({"voice": 123, "chat": CHAT_DIGEST}), "lowercase hex"),
        (json.dumps({"voice": VOICE_DIGEST, "chat": VOICE_DIGEST}), "own token"),
    ],
)
def test_invalid_auth_config_is_rejected(secrets_dir: Path, content: str, message: str) -> None:
    _write(secrets_dir / "auth.json", content)
    with pytest.raises(ConfigError, match=message):
        load_config()


def test_auth_config_accessible_by_others_is_rejected(secrets_dir: Path) -> None:
    os.chmod(secrets_dir / "auth.json", 0o644)
    with pytest.raises(ConfigError, match="accessible by other users"):
        load_config()


def test_startup_check_exits_with_code_1(
    secrets_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (secrets_dir / "hmac_key").unlink()
    with pytest.raises(SystemExit) as exc:
        load_config_or_exit()
    assert exc.value.code == 1
    assert "Startup check failed" in capsys.readouterr().err
