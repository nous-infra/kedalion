"""Configuration loading and startup check.

Non-secret settings come from environment variables (prefix KEDALION_).
Secrets are read from files (e.g. mounted at /run/secrets), never from
environment variables. Any missing or invalid value aborts the start –
there is no open fallback. Error messages never contain secret values.
"""

from __future__ import annotations

import json
import re
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from pydantic import AnyHttpUrl, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

CHANNELS = ("voice", "chat")
HMAC_KEY_FILENAME = "hmac_key"
MIN_KEY_BYTES = 32
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")  # SHA-256, lowercase hex


class ConfigError(Exception):
    """Configuration is missing or invalid."""


class Settings(BaseSettings):
    """Non-secret settings from the environment or a local .env file."""

    model_config = SettingsConfigDict(
        env_prefix="KEDALION_", env_file=".env", extra="ignore"
    )

    ollama_url: AnyHttpUrl
    ollama_model: str = Field(min_length=1)
    ollama_timeout_seconds: float = Field(default=120, gt=0, le=600)
    secrets_dir: Path = Path("/run/secrets")
    auth_config_path: Path


@dataclass(frozen=True)
class Config:
    """Validated runtime configuration. Secret fields are hidden from repr."""

    settings: Settings
    hmac_key: bytes = field(repr=False)
    channel_digests: Mapping[str, bytes] = field(repr=False)


def _read_protected_file(path: Path, label: str) -> str:
    """Read a text file that must not be accessible by other users."""
    if not path.is_file():
        raise ConfigError(f"{label} not found: {path}")
    if path.stat().st_mode & (stat.S_IROTH | stat.S_IWOTH):
        raise ConfigError(f"{label} is accessible by other users: {path}")
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        raise ConfigError(f"{label} is not readable: {path}") from None


def _load_hmac_key(secrets_dir: Path) -> bytes:
    raw = _read_protected_file(secrets_dir / HMAC_KEY_FILENAME, "HMAC key")
    if not re.fullmatch(r"(?:[0-9a-fA-F]{2})+", raw):
        raise ConfigError("HMAC key must be hex-encoded")
    key = bytes.fromhex(raw)
    if len(key) < MIN_KEY_BYTES:
        raise ConfigError(f"HMAC key must be at least {MIN_KEY_BYTES} bytes")
    return key


def _load_channel_digests(path: Path) -> Mapping[str, bytes]:
    raw = _read_protected_file(path, "Auth config")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ConfigError("Auth config is not valid JSON") from None
    if not isinstance(data, dict) or set(data) != set(CHANNELS):
        raise ConfigError(f"Auth config must contain exactly: {', '.join(CHANNELS)}")

    digests: dict[str, bytes] = {}
    for channel in CHANNELS:
        value = data[channel]
        if not isinstance(value, str) or not DIGEST_PATTERN.fullmatch(value):
            raise ConfigError(f"Digest for '{channel}' must be 64 lowercase hex chars")
        digests[channel] = bytes.fromhex(value)

    if len(set(digests.values())) != len(digests):
        raise ConfigError("Each channel needs its own token")
    return MappingProxyType(digests)


def load_config() -> Config:
    """Load and validate the full configuration or raise ConfigError."""
    try:
        settings = Settings()
    except ValidationError as exc:
        # Only report field names, never the submitted values
        names = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
        raise ConfigError(f"Invalid or missing settings: {', '.join(names)}") from None

    return Config(
        settings=settings,
        hmac_key=_load_hmac_key(settings.secrets_dir),
        channel_digests=_load_channel_digests(settings.auth_config_path),
    )


def load_config_or_exit() -> Config:
    """Startup check: return the config or stop the process with exit code 1."""
    try:
        return load_config()
    except ConfigError as exc:
        print(f"Startup check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    config = load_config_or_exit()
    print(f"Config OK – channels: {', '.join(config.channel_digests)}")
