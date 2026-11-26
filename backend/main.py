"""Entry point for uvicorn: run the startup check, then build the app."""

from backend.app import create_app
from backend.config import load_config_or_exit

app = create_app(load_config_or_exit())
