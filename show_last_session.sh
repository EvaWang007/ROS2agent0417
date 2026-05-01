#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_LOG="$ROOT/nav_ws/logs/rosa_session.jsonl"
TOOLS_LOG="$ROOT/nav_ws/logs/rosa_tools.jsonl"

if [[ ! -f "$SESSION_LOG" ]]; then
  echo "Session log not found: $SESSION_LOG"
  exit 1
fi
if [[ ! -f "$TOOLS_LOG" ]]; then
  echo "Tools log not found: $TOOLS_LOG"
  exit 1
fi

last_session_line="$(tail -n 1 "$SESSION_LOG")"
if [[ -z "$last_session_line" ]]; then
  echo "Session log is empty."
  exit 1
fi

query_id="$(printf '%s\n' "$last_session_line" | sed -n 's/.*"query_id": "\([^"]*\)".*/\1/p')"
if [[ -z "$query_id" ]]; then
  echo "Could not parse query_id from last session line:"
  echo "$last_session_line"
  exit 1
fi

echo "=== Last session query_id ==="
echo "$query_id"
echo

echo "=== Session events for this query_id ==="
grep '"query_id": '"\"$query_id\""'' "$SESSION_LOG" || true
echo

echo "=== Tool events for this query_id ==="
grep '"query_id": '"\"$query_id\""'' "$TOOLS_LOG" || true
echo

echo "Tip: if you want only the latest few events, run:"
echo "  grep '"\"query_id\"": \"$query_id\"' $TOOLS_LOG | tail -n 20"
