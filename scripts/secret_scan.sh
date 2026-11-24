#!/usr/bin/env bash
# Secret scan of the git index – runs as pre-commit hook.
# Generic patterns:  scripts/secret_patterns.txt (in repo)
# Personal patterns: .scan-patterns.local (local only, never committed)
# To allow a single line on purpose, add the comment "scan:allow".
set -uo pipefail

cd "$(git rev-parse --show-toplevel)" || exit 1
FOUND=0

# 1) Forbidden files in the index
BAD_FILES="$(git diff --cached --name-only --diff-filter=ACMR \
  | grep -E '(^|/)(\.env(\..+)?|[^/]+\.(db|sqlite3?|key|pem)|docker-compose\.override\.yml)$' \
  | grep -vE '(^|/)\.env\.example$')"
if [ -n "$BAD_FILES" ]; then
  echo "BLOCKED – these files must never be committed:"
  echo "$BAD_FILES"
  FOUND=1
fi

# 2) Check content of all indexed files against both pattern lists
for LIST in scripts/secret_patterns.txt .scan-patterns.local; do
  [ -f "$LIST" ] || continue
  PATTERNS="$(mktemp)"
  # Strip comments and blank lines (a blank pattern would match everything)
  grep -vE '^[[:space:]]*(#|$)' "$LIST" > "$PATTERNS"
  if [ -s "$PATTERNS" ]; then
    HITS="$(git grep --cached -nIiE -f "$PATTERNS" -- . \
      ':!scripts/secret_patterns.txt' ':!backend/requirements.txt' \
      | grep -v 'scan:allow')"
    if [ -n "$HITS" ]; then
      echo "BLOCKED – matches from $LIST:"
      echo "$HITS"
      FOUND=1
    fi
  fi
  rm -f "$PATTERNS"
done

if [ "$FOUND" -ne 0 ]; then
  echo "Commit aborted."
  exit 1
fi
echo "Secret scan: no matches."
