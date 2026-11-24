"""Create the HMAC key (if missing) and one token per channel.

Tokens are printed once and never stored; only their digests are written
to the auth config. Run from the repo root:

    python -m scripts.create_channel_tokens --secrets-dir secrets
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from backend.api.tokens import token_digest
from backend.config import CHANNELS, HMAC_KEY_FILENAME, MIN_KEY_BYTES


def _write_private(path: Path, content: str) -> None:
    """Create a file readable only by its owner; fail if it already exists."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content + "\n")


def _load_or_create_key(path: Path) -> bytes:
    if path.exists():
        return bytes.fromhex(path.read_text(encoding="utf-8").strip())
    key_hex = secrets.token_hex(MIN_KEY_BYTES)
    _write_private(path, key_hex)
    print(f"Created new HMAC key: {path}")
    return bytes.fromhex(key_hex)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create channel tokens.")
    parser.add_argument("--secrets-dir", type=Path, required=True)
    parser.add_argument("--auth-config", type=Path,
                        help="default: <secrets-dir>/auth.json")
    parser.add_argument("--force", action="store_true",
                        help="replace existing auth config (invalidates all tokens)")
    args = parser.parse_args()

    auth_path = args.auth_config or args.secrets_dir / "auth.json"
    if auth_path.exists() and not args.force:
        raise SystemExit(f"{auth_path} exists – use --force to replace it")

    args.secrets_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = _load_or_create_key(args.secrets_dir / HMAC_KEY_FILENAME)

    tokens = {channel: secrets.token_urlsafe(32) for channel in CHANNELS}
    digests = {channel: token_digest(key, tok).hex() for channel, tok in tokens.items()}

    if auth_path.exists():
        auth_path.unlink()
    _write_private(auth_path, json.dumps(digests, indent=2))

    print(f"Wrote {auth_path}")
    print("Tokens (shown once – store them in the clients now):")
    for channel, tok in tokens.items():
        print(f"  {channel}: {tok}")


if __name__ == "__main__":
    main()
