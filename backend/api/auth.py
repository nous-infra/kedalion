"""Token authentication. The channel is derived from the token alone."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.tokens import token_digest
from backend.config import Config

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    # Same response for every failure – no hint why the request was rejected
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )


def match_channel(config: Config, token: str) -> str | None:
    """Return the channel for a token, or None.

    Compares against every channel without stopping early, so the response
    time does not reveal which channel matched.
    """
    digest = token_digest(config.hmac_key, token)
    matched = None
    for channel, expected in config.channel_digests.items():
        if hmac.compare_digest(digest, expected):
            matched = channel
    return matched


def require_channel(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """FastAPI dependency: return the caller's channel or reject with 401."""
    if credentials is None:
        raise _unauthorized()
    channel = match_channel(request.app.state.config, credentials.credentials)
    if channel is None:
        raise _unauthorized()
    return channel


Channel = Annotated[str, Depends(require_channel)]
