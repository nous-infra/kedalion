# Kedalion

A self-hosted personal agent for voice and chat. Kedalion receives requests
through an OpenAI-compatible API, runs a local LLM via Ollama and acts through
MCP tools – guarded by a permission layer that decides independently of the
model.

> **Status:** early development – not ready for use.

## Goals

- **Local only** – no cloud APIs; the model runs on your own hardware via Ollama.
- **Voice and chat** – Home Assistant Assist (voice) and a chat client share one agent.
- **Context-aware actions** – e.g. "I'm cooking now" → check time and daylight,
  then switch on the kitchen light.
- **Security first** – see below.

## Architecture

Each building block has exactly one job and lives in its own package.
`main.py` only starts the app and wires the modules together.

| Package               | Responsibility                                              |
|-----------------------|-------------------------------------------------------------|
| `backend/api`         | OpenAI-compatible endpoint, token auth, channel detection   |
| `backend/agent`       | Agent loop: ask the model, run tool calls, finish the answer |
| `backend/llm`         | Ollama client – the only place that knows the model         |
| `backend/tools`       | MCP client (Home Assistant first, more apps later)          |
| `backend/permissions` | Checks every tool call; approvals for private data          |
| `backend/memory`      | Profile and long-term memory                                |
| `backend/chatlog`     | Conversation log with rating field                          |

## Security principles

- **Per-client tokens.** Each client gets its own random token. The server only
  stores `HMAC-SHA256(key, token)` and compares in constant time. The channel
  (voice/chat) is derived from the token, never from client input.
- **Fail-closed startup.** Missing or invalid configuration stops the process.
  There is no open fallback.
- **Secrets as files.** Keys and tokens are read from protected files
  (e.g. mounted at `/run/secrets`), never from environment variables, the repo
  or the image. Files readable by other users are rejected.
- **Tool output is data.** Results from tools are never treated as instructions.
  The permission layer decides independently of the model.
- **Permission tiers.** Tools are tiered (free / personal / private). Private
  data needs explicit approval via a one-time, signed, short-lived link;
  write actions need confirmation.
- **Supply chain.** Dependencies are pinned with hashes (`pip-tools`).
- **Secret scan.** A pre-commit hook blocks secrets and forbidden files.

## Development setup

Requires Python 3.14.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r backend/requirements.txt
ln -s ../../scripts/secret_scan.sh .git/hooks/pre-commit
cp .env.example .env    # then adjust the values
```

For local development, point the secrets to the git-ignored `secrets/` folder
in `.env` (`KEDALION_SECRETS_DIR=secrets`,
`KEDALION_AUTH_CONFIG_PATH=secrets/auth.json`), then create key and tokens and
run the startup check:

```sh
python -m scripts.create_channel_tokens --secrets-dir secrets
python -m backend.config
```

Tokens are printed once and never stored. Put them into the clients; if one is
lost, create new ones with `--force`.

## Configuration

| Variable                    | Description                         | Default        |
|-----------------------------|-------------------------------------|----------------|
| `KEDALION_OLLAMA_URL`       | Ollama base URL                     | –              |
| `KEDALION_OLLAMA_MODEL`     | Model name                          | –              |
| `KEDALION_SECRETS_DIR`      | Directory containing `hmac_key`     | `/run/secrets` |
| `KEDALION_AUTH_CONFIG_PATH` | JSON file with channel digests      | –              |

## Dependencies

Edit `backend/requirements.in`, then regenerate the lockfile:

```sh
pip install pip-tools
pip-compile --generate-hashes --strip-extras \
  -o backend/requirements.txt backend/requirements.in
pip install --require-hashes -r backend/requirements.txt
```

## Secret scan

`scripts/secret_scan.sh` runs on every commit. Generic patterns live in
`scripts/secret_patterns.txt`. Personal patterns (own IP ranges, domains,
names) go into `.scan-patterns.local`, which is git-ignored. Add the comment
`scan:allow` to a line to accept a known false positive.

## License

Not decided yet. Until a license is added, all rights are reserved.
