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

export AWS_PROFILE="${AWS_PROFILE:-tracevault}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export TRACEVAULT_TENANT_ID="${TRACEVAULT_TENANT_ID:-tenant-a}"

# Prefer a real interpreter; PATH may contain a broken Windows python shim.
_json_key() {
  if command -v jq >/dev/null 2>&1; then
    jq -r .key
  else
    (cd "$ROOT/demo-app" && uv run python -c 'import json,sys; print(json.load(sys.stdin)["key"])')
  fi
}

# Ingest: API base (no /v1/traces). Prefer env, else terraform api_url, else known dev endpoint.
if [[ -z "${TRACEVAULT_INGEST_URL:-}" ]]; then
  if command -v terraform >/dev/null 2>&1 && [[ -d "$ROOT/infra" ]]; then
    TRACEVAULT_INGEST_URL="$(terraform -chdir="$ROOT/infra" output -raw api_url 2>/dev/null || true)"
  fi
  export TRACEVAULT_INGEST_URL="${TRACEVAULT_INGEST_URL:-https://55qm437628.execute-api.us-east-1.amazonaws.com}"
fi

# Tenant key from Secrets Manager when unset (never echo the value).
if [[ -z "${TRACEVAULT_TENANT_KEY:-}" ]]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "TRACEVAULT_TENANT_KEY unset and aws CLI missing" >&2
    exit 1
  fi
  secret_json="$(aws secretsmanager get-secret-value \
    --secret-id "tracevault-dev/ingest/${TRACEVAULT_TENANT_ID}" \
    --query SecretString --output text)"
  export TRACEVAULT_TENANT_KEY="$(printf '%s' "$secret_json" | _json_key)"
  unset secret_json
  if [[ -z "${TRACEVAULT_TENANT_KEY}" || "${#TRACEVAULT_TENANT_KEY}" -lt 8 ]]; then
    echo "failed to resolve TRACEVAULT_TENANT_KEY from Secrets Manager" >&2
    exit 1
  fi
fi

# P-15: TRACEVAULT_FAKE_BEDROCK=1 is a stub. Leave unset for live Bedrock.
cd "$ROOT/demo-app"
set +e
uv run python -m demo_app.main \
  --pii \
  --tenant tenant-a \
  --question "What is retention?"
rc=$?
set -e

# Fall back to fake Bedrock only when the live model path failed (not ingest 401/5xx).
if [[ $rc -ne 0 && "${TRACEVAULT_FAKE_BEDROCK:-}" != "1" ]]; then
  echo "demo exited ${rc}; retrying once with TRACEVAULT_FAKE_BEDROCK=1 (P-15 stub)" >&2
  export TRACEVAULT_FAKE_BEDROCK=1
  uv run python -m demo_app.main \
    --pii \
    --tenant tenant-a \
    --question "What is retention?"
fi

INGEST="${TRACEVAULT_INGEST_URL:-}"
echo "flight emitted"
if [[ -n "$INGEST" ]]; then
  echo "ingest ${INGEST}"
else
  echo "ingest unset"
fi
if [[ "${TRACEVAULT_FAKE_BEDROCK:-}" == "1" ]]; then
  echo "bedrock: fake (TRACEVAULT_FAKE_BEDROCK=1)"
else
  echo "bedrock: live"
fi
