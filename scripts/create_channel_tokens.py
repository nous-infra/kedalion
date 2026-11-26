"""Create the HMAC key (if missing) and channel tokens.

Tokens are printed once and never stored; only their digests are written
to the auth config. Run from the repo root:

    python -m scripts.create_channel_tokens --secrets-dir secrets
    python -m scripts.create_channel_tokens --secrets-dir secrets --channel voice
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from backend.api.tokens import token_digest
from backend.config import CHANNELS, HMAC_KEY_FILENAME, MIN_KEY_BYTES


def _write_private(path: Path, content: str, *, replace: bool = False) -> None:
    """Write a file readable only by its owner.

    Without replace, an existing file is never touched. With replace, the
    content goes to a temp file first and is swapped in atomically.
    """
    if replace:
        tmp = path.with_name(path.name + ".tmp")
        tmp.unlink(missing_ok=True)
        _write_private(tmp, content)
        os.replace(tmp, path)
        return
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
    parser.add_argument("--channel", choices=CHANNELS,
                        help="renew only this channel (needs existing key and auth config)")
    parser.add_argument("--force", action="store_true",
                        help="replace all tokens (invalidates every client)")
    args = parser.parse_args()

    auth_path = args.auth_config or args.secrets_dir / "auth.json"
    key_path = args.secrets_dir / HMAC_KEY_FILENAME

    if args.channel:
        if not (auth_path.exists() and key_path.exists()):
            raise SystemExit("--channel needs an existing key and auth config")
        digests = json.loads(auth_path.read_text(encoding="utf-8"))
        channels = [args.channel]
    else:
        if auth_path.exists() and not args.force:
            raise SystemExit(f"{auth_path} exists – use --force or --channel")
        args.secrets_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        digests = {}
        channels = list(CHANNELS)

    key = _load_or_create_key(key_path)
    tokens = {channel: secrets.token_urlsafe(32) for channel in channels}
    digests.update({channel: token_digest(key, tok).hex() for channel, tok in tokens.items()})
    _write_private(auth_path, json.dumps(digests, indent=2), replace=auth_path.exists())

    print(f"Wrote {auth_path}")
    print("Tokens (shown once – store them in the clients now):")
    for channel, tok in tokens.items():
        print(f"  {channel}: {tok}")


if __name__ == "__main__":
    main()
