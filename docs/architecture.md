# Architecture

## The big picture

```
  Voice (Home Assistant)        Chat client
            \                     /
             ▼                   ▼
   ┌─────────────── Kedalion ───────────────┐
   │ api          token check, request rules │
   │ agent        the agent loop             │
   │ permissions  is this tool call allowed? │
   │ tools        MCP clients                │
   │ llm          talks to Ollama            │
   │ memory       what Kedalion knows        │
   │ chatlog      conversation log           │
   └─────────────────────────────────────────┘
             │                   │
             ▼                   ▼
   Ollama (GPU machine)    Tools: Home Assistant, …
```

Simple commands like "light on" are handled by Home Assistant itself.
Everything else goes to Kedalion.

## Building blocks

Each package has exactly one job.

| Package | Job | Status |
|---------|-----|--------|
| `api` | Receives requests, checks the token, enforces the request rules | Built (chat answer is a placeholder) |
| `agent` | Asks the model, runs tool calls, decides when the answer is done | Planned |
| `llm` | The only place that talks to Ollama. Changing the model only touches this package | Client built, not yet used by the API |
| `tools` | Connects to tools via MCP – Home Assistant first, more apps later | Planned |
| `permissions` | Checks every tool call, independently of the model | Planned |
| `memory` | Profile and long-term memory | Planned |
| `chatlog` | Logs conversations with a rating field for later training | Planned |

## What happens at startup

1. `backend/main.py` runs the **startup check** (`load_config_or_exit`).
2. If anything is missing or invalid, the process stops with exit code 1 –
   before a network port is opened.
3. If everything is fine, `backend/app.py` builds the app with the checked config.

## What happens on a request (today)

1. The token is checked. Wrong or missing → `401`.
2. The channel (voice or chat) is derived from the token.
3. The request rules are checked (see [Chat API](api.md)). Broken → `422`.
4. The placeholder answers with channel and message count.

## Files

| File | Purpose |
|------|---------|
| `backend/main.py` | Entry point: startup check, then build the app. No logic. |
| `backend/app.py` | Builds the FastAPI app and wires the routers |
| `backend/config.py` | Reads settings and secrets, runs the startup check |
| `backend/api/auth.py` | Token check and channel detection |
| `backend/api/tokens.py` | Computes token digests (shared by server and script) |
| `backend/api/schemas.py` | Request/response format and request rules |
| `backend/api/chat.py` | The chat endpoint |
| `backend/api/health.py` | `/health` for Docker and monitoring |
| `scripts/create_channel_tokens.py` | Creates the key and client tokens |
| `scripts/secret_scan.sh` | Pre-commit secret scan |
| `tests/` | Automated tests (`python -m pytest`) |

## Code rules

- One job per package, one topic per file, at most 250 lines per file.
- No logic in `main.py`.
- All files in English.
- One logical change per commit; every commit passes the secret scan.
