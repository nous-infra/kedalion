"""Application factory: build the FastAPI app for a validated config."""

from fastapi import FastAPI

from backend.api import chat, health
from backend.config import Config


def create_app(config: Config) -> FastAPI:
    # Interactive docs and the OpenAPI schema are disabled on purpose:
    # they would expose the whole API to anyone who can reach the port.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.config = config
    app.include_router(health.router)
    app.include_router(chat.router)
    return app
