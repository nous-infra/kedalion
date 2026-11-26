# Chat API

Kedalion speaks the **OpenAI-compatible chat format**. This is a common JSON
format for talking to language models. OpenAI is not involved – many tools
simply understand this format, so clients can connect without a custom adapter.

> **Status:** placeholder. Kedalion checks the request and answers with the
> detected channel and the number of messages it would use. The real agent
> comes later.

## Endpoint

```
POST /v1/chat/completions
Authorization: Bearer <token>
```

Every client (voice, chat) has its own token. Kedalion knows the channel
**from the token alone** – a client cannot choose its channel.

## Request

```json
{
  "messages": [
    {"role": "user",      "content": "Turn on the light"},
    {"role": "assistant", "content": "Which room?"},
    {"role": "user",      "content": "Kitchen"}
  ]
}
```

- `messages` is the **whole conversation so far**. The API does not remember
  anything between requests – the client sends the history every time. That
  is how Kedalion understands that "Kitchen" belongs to "Turn on the light".
- `model` is ignored – the answer always comes from Kedalion.
- Unknown fields are ignored.

### Rules

| Rule | Why |
|------|-----|
| Only `user` and `assistant` messages are used. `system`, `developer` and `tool` messages from the client are dropped. | The history comes from the client and cannot be trusted. A client could send its own rules ("ignore all rules") or fake tool results. Kedalion always uses its own system prompt. |
| The conversation must end with a `user` message. | Otherwise there is nothing to answer. |
| At most 50 messages, each at most 8000 characters. | Limits memory use and model load. |
| `content` must be plain text. | Images and multi-part messages are not supported. |
| `stream` must be `false` (or missing). | Streaming is not supported yet. |

The token is checked **before** these rules. Without a valid token, nobody
learns what Kedalion accepts.

## Response

```json
{
  "id": "chatcmpl-…",
  "object": "chat.completion",
  "created": 1795723324,
  "model": "kedalion",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Kitchen light is on."},
    "finish_reason": "stop"
  }]
}
```

A client only needs `choices[0].message.content` – the answer text. For voice,
this is the text that gets spoken.

## Errors

| Code | Meaning |
|------|---------|
| `401` | Token missing or wrong. Always the same answer, no hint why. |
| `422` | The request breaks one of the rules above. |

## Tools – what happens behind the scenes

Clients never see tool calls. They send text and get text back. Everything in
between happens inside Kedalion:

```
Client ──text──▶ Kedalion ──text + list of tools──▶ Model (Ollama)
                    │   ◀──"please call tool X"─────────┘
                    ▼
             Permission check ──▶ Tool (e.g. Home Assistant)
                    │
                    └──tool result──▶ Model … until the model answers with text
```

1. Kedalion sends the conversation and a list of available tools to the model.
2. The model either answers with text (done) or asks for a tool call.
3. Kedalion's permission layer decides if the call is allowed – independently
   of the model.
4. The tool result goes back to the model, and the loop repeats.

This loop is the **agent loop**. Because it runs inside Kedalion, no client can
bypass the permission checks.

## Not supported yet

- Streaming (answer arriving piece by piece)
- Images and multi-part content
- Tools sent by the client
- A hard limit on request size before parsing (planned with rate limiting)
