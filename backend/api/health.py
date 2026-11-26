"""Liveness endpoint for Docker and monitoring. No auth, no details."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
