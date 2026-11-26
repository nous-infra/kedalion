# Security

## What we protect against

| Threat | Example |
|--------|---------|
| Someone on the network | A device in the LAN or VPN sends requests to Kedalion |
| A stolen or leaked file | The auth config ends up somewhere it should not |
| A manipulated conversation | A client sends fake rules or fake tool results |
| Manipulated tool output | A tool result contains text like "ignore your rules" |
| A leaked repository | Secrets or personal data committed by mistake |
| Bad packages | A dependency is replaced or tampered with |

## Measures

### Tokens – who may talk to Kedalion
- **What:** Every client gets its own random token. Kedalion stores only a
  fingerprint of it (`HMAC-SHA256` with a secret key), never the token itself.
- **Why:** If the stored fingerprints leak, they are useless without the key,
  which is stored separately.
- **What:** The channel (voice or chat) is derived from the token alone.
- **Why:** A client cannot pretend to be another channel.
- **What:** Kedalion compares against every channel without stopping early.
- **Why:** The response time does not reveal which channel matched.
- **What:** Every failure gets the same `401` answer.
- **Why:** An attacker learns nothing about why the token failed.
- **Renewing:** `--channel <name>` renews one token without affecting the
  others. The server reads tokens only at startup – restart after renewing.

### Secrets – keys and tokens
- **What:** Secrets are read from files, never from environment variables.
- **Why:** Environment variables show up in `docker inspect`, process listings
  and crash reports.
- **What:** Secret files that other users can read are rejected.
- **What:** Secret values are hidden when the config is printed or logged, and
  error messages contain field names only, never values.

### Fail-closed startup
- **What:** Missing or invalid configuration stops Kedalion before it opens a port.
- **Why:** There is never a state where Kedalion runs "open" by accident.

### API hardening
- **What:** No interactive API docs, no server header, minimal `/health`.
- **Why:** Less information for anyone probing the port.
- **What:** The token is checked before the request rules.
- **Why:** Without a token, nobody learns what Kedalion accepts.

### Untrusted input
- **What:** `system`, `developer` and `tool` messages from clients are dropped;
  Kedalion uses its own system prompt. Message count and length are limited.
- **Why:** The conversation history comes from the client. It could contain
  fake rules or fake tool results.
- **Planned:** Tool results are treated as data, never as instructions.
- **Planned:** The permission layer decides about every tool call
  independently of the model – even a fooled model cannot do more than allowed.

### Permission tiers (planned)
| Tier | Examples | Rule |
|------|----------|------|
| Free | Lights, devices, weather, records | Allowed |
| Personal | Training, profile | Allowed, not spoken aloud on voice |
| Private | Journal, later sleep data | Only after explicit approval |
| Write | Changing data | Needs confirmation (exception: dictating a journal entry) |

Approvals for private data never use spoken passwords – they could be overheard
and would end up in transcripts and logs. Instead, a push notification with an
"Approve" button is sent to the phone. The button carries a one-time, signed,
short-lived code.

### Supply chain
- **What:** All dependencies are pinned with exact versions and checksums
  (`pip-tools --generate-hashes`).
- **Why:** pip refuses any package whose checksum does not match.
- **What:** Development tools are in a separate lockfile and never shipped.
- **What:** Unknown packages are checked before they are added (similar names
  are a common trick).

### Repository hygiene
- **What:** A pre-commit hook scans every commit for secrets and forbidden
  files (`.env`, databases, keys).
- **What:** Personal patterns (own IP ranges, domains, names) live in a local,
  git-ignored file, so the scanner itself reveals nothing.
- **What:** No personal data in code – real values only in `.env` and local
  config files. The repository is written so it could become public.

## Before the first real deployment

- Rate limiting and a hard request size limit
- Docker with a bridge network and an explicitly published port
- Reachable only from the LAN or VPN
- Backups, tested restore
- A short security review
