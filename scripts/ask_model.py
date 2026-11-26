"""Send one question to the model and print the answer and how long it took.

Development helper to test the model connection. Run from the repo root:

    python -m scripts.ask_model "Say hello in one sentence."
"""

from __future__ import annotations

import argparse
import asyncio
import time

from backend.config import load_config_or_exit
from backend.llm.ollama import LLMError, OllamaClient


async def _ask(question: str) -> int:
    settings = load_config_or_exit().settings
    client = OllamaClient(
        str(settings.ollama_url), settings.ollama_model, settings.ollama_timeout_seconds
    )
    started = time.monotonic()
    try:
        reply = await client.chat([{"role": "user", "content": question}])
    except LLMError as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        await client.aclose()
    print(reply.content)
    print(f"--- {time.monotonic() - started:.1f} s")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the model one question.")
    parser.add_argument("question")
    raise SystemExit(asyncio.run(_ask(parser.parse_args().question)))


if __name__ == "__main__":
    main()
