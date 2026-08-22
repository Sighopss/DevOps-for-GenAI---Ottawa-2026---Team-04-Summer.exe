#!/usr/bin/env bash
# #49 failure demo — ingest unreachable → sdk/.last-flight.json, process exits 0.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LAST_FLIGHT="$ROOT/sdk/.last-flight.json"
rm -f "$LAST_FLIGHT"

# Blackhole: nothing accepts TCP on port 1.
export TRACEVAULT_INGEST_URL="${TRACEVAULT_INGEST_URL_BLACKHOLE:-http://127.0.0.1:1}"
unset TRACEVAULT_TENANT_KEY || true
export TRACEVAULT_FAKE_BEDROCK=1
export TRACEVAULT_TENANT_ID="${TRACEVAULT_TENANT_ID:-tenant-a}"

echo "demo_ingest_down: TRACEVAULT_INGEST_URL=${TRACEVAULT_INGEST_URL}"
echo "demo_ingest_down: expecting local fallback at sdk/.last-flight.json"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv missing" >&2
  exit 1
fi

cd "$ROOT/sdk"
uv run python - <<'PY'
from tracevault import TraceVaultClient, start_span

client = TraceVaultClient.from_env()
with start_span(client, kind="http", name="demo_ingest_down"):
    with start_span(
        client,
        kind="llm",
        name="chat",
        model="demo-model",
        sensitive=True,
        prompt="demo only — no live PII required",
    ):
        pass
client.flush()
print("sdk flush completed without raising")
PY

if [[ ! -f "$LAST_FLIGHT" ]]; then
  echo "FAIL: expected $LAST_FLIGHT after unreachable ingest" >&2
  exit 1
fi

echo "OK: wrote $LAST_FLIGHT (fallback only — not the product)"
wc -c "$LAST_FLIGHT"
