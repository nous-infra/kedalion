"""Channel token digests.

Clients hold a random token; the server only stores HMAC-SHA256(key, token).
"""

import hashlib
import hmac


def token_digest(key: bytes, token: str) -> bytes:
    """Return the HMAC-SHA256 digest of a client token."""
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).digest()
