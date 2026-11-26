# Decisions

Why things are the way they are. Newest at the bottom.

| Decision | Why |
|----------|-----|
| Kedalion runs on its own machine; the model runs on a separate GPU machine | The model can be swapped without touching Kedalion; the GPU machine stays simple |
| Only Ollama, no cloud model client in the code | Everything stays local |
| OpenAI-compatible API | Many clients understand it – no custom adapters needed |
| Separate token per client; the channel comes from the token | Clients cannot choose or fake their channel |
| Tokens stored only as HMAC digests | A leaked auth config is useless without the key |
| Secrets as files, not environment variables | Environment variables leak into `docker inspect`, logs and crash reports |
| Fail-closed startup check | Kedalion never runs half-configured |
| Package `chatlog` instead of `logging` | A package named `logging` would hide Python's own `logging` module |
| `pip-tools` with hashes | Same versions everywhere; tampered packages are rejected |
| Separate dev lockfile that includes the runtime list | Runtime and dev packages always fit together; dev tools never ship |
| `uvicorn` without `[standard]` extras | Fewer packages, smaller attack surface |
| `httpx2` for the test client | Starlette deprecated `httpx` for its test client; `httpx2` is maintained by the Pydantic team (checked before adding) |
| Start uvicorn via `python -m uvicorn` | The shell may remember an old `uvicorn` from another Python |
| Interactive API docs disabled | They would show the whole API to anyone who can reach the port |
| Drop `system`, `developer` and `tool` messages from clients | Client history cannot be trusted; Kedalion sets its own rules |
| No streaming at first | Simpler; added later if voice latency needs it |
| No spoken passwords for approvals | Could be overheard; would end up in transcripts and logs |
| All files in English | The repository may become public |
| Private repository in its own GitHub organization | Groups related repos; can go public after a review |
| Pre-commit secret scan with local personal patterns | Catches mistakes before they enter git history |
| Ollama's own chat API instead of its OpenAI-compatible one | Supports options like turning off "thinking" |
| `httpx2` as runtime HTTP client | Same library as the tests; maintained by the Pydantic team |
| Async model client | Tools (MCP) will be async too |
| Proxy variables ignored for model requests | Requests to the model cannot be redirected through the environment |
| Model errors never include response bodies | They could contain internal details |
| Development tunnel on local port 11435 | A local Ollama on the dev machine already uses 11434 – avoids talking to the wrong model |
