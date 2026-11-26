# Model connection (llm)

Kedalion talks to the model through one class: `OllamaClient` in
`backend/llm/ollama.py`. Nothing else in Kedalion knows about Ollama.
To use another model or server later, only this package changes.

## What Kedalion sends

```json
{
  "model": "gemma4:26b",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false,
  "think": false,
  "tools": [ ... ]
}
```

- It uses Ollama's own chat API (`/api/chat`), not Ollama's OpenAI-compatible
  one, because only the own API supports options like `think`.
- `think: false` turns off the model's "thinking" phase – faster answers.
- `tools` is only sent when there are tools to offer.

## What comes back

A reply has two parts:

- `content` – the answer text (may be empty when the model wants a tool)
- `tool_calls` – a list of tool calls, each with a `name` and `arguments`

The format is checked strictly. The model's output is data – tool calls still
have to pass the permission layer (planned) before anything happens.

## When something goes wrong

Every failure becomes one error type (`LLMError`) with a short message:

| Situation | Message |
|-----------|---------|
| No answer in time | `model timed out` |
| Ollama answers with an HTTP error | `model returned HTTP <code>` |
| Ollama not reachable, or not JSON | `model not reachable or invalid response` |
| Wrong answer format | `invalid response format` / `invalid tool call format` |

Response bodies are never shown – they could contain internal details.

## Timeouts

- 5 seconds to connect.
- `KEDALION_OLLAMA_TIMEOUT_SECONDS` (default 120) to wait for the answer.
  Large models need time, especially when they first have to be loaded.

## Safety

- Proxy environment variables are ignored, so requests cannot be redirected
  through the environment.
- Redirects are not followed.

## Testing the connection

The model server only accepts connections from the Kedalion host. For
development on another machine, use an SSH tunnel through that host:

```sh
ssh -p <ssh-port> -N -L 127.0.0.1:11435:<model-host>:11434 <user>@<kedalion-host>
```

Then set `KEDALION_OLLAMA_URL=http://127.0.0.1:11435` in `.env` and run:

```sh
python -m scripts.ask_model "Say hello in one short sentence."
```

The tunnel uses port 11435 on purpose: if Ollama also runs locally, it already
uses 11434 – and Kedalion would silently talk to the wrong model.
