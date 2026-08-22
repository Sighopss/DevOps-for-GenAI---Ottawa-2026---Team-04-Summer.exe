#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d "$ROOT/demo-app" ]]; then
  echo "demo-app missing (trevor-demo)" >&2
  exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv missing" >&2
  exit 1
fi

export TRACEVAULT_TENANT_ID="${TRACEVAULT_TENANT_ID:-tenant-a}"

# P-15: TRACEVAULT_FAKE_BEDROCK=1 is a stub. Unset it for live Bedrock.
cd "$ROOT/demo-app"
uv run python -m demo_app.main \
  --pii \
  --tenant tenant-a \
  --question "What is retention?"

INGEST="${TRACEVAULT_INGEST_URL:-}"
echo "flight emitted"
if [[ -n "$INGEST" ]]; then
  echo "ingest ${INGEST}"
else
  echo "ingest unset"
fi
