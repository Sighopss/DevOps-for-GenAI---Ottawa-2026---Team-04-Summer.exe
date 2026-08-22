#!/usr/bin/env bash
# Red-team harness for TraceVault (issue #54). Reproduces docs/RED_TEAM.md.
#
# Unauthenticated attacks (A*) run with no secrets. Authenticated attacks (B*)
# run only when the operator exports credentials they hold out of band:
#   TENANT_A_KEY   real X-Tenant-Key for tenant-a   (from Trevor / Secrets Manager)
#   TENANT_B_JWT   Cognito *ID* token for tenant-b  (sign in at the hosted UI)
#   TENANT_A_JWT   Cognito *ID* token for tenant-a
# No secret is written to disk or echoed. Usage:  bash docs/redteam/redteam.sh
set -u

API="${TRACEVAULT_API:-https://55qm437628.execute-api.us-east-1.amazonaws.com}"
EDGE="${TRACEVAULT_EDGE:-https://d13b678j60bhap.cloudfront.net}"
TRACE_A="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
pass=0 fail=0

# check <label> <expected-substr> <actual>
check() {
  if printf '%s' "$3" | grep -q "$2"; then echo "  PASS  $1"; pass=$((pass+1))
  else echo "  FAIL  $1 — expected /$2/, got: $3"; fail=$((fail+1)); fi
}
hit() { curl -s -w "|%{http_code}" "$@"; }

b64url() {
  printf '%s' "$1" | base64 | tr -d '\n=' | tr '/+' '_-'
}

forge_unsigned_jwt() {
  printf '%s.%s.' "$(b64url '{"alg":"none"}')" "$(b64url '{"custom:tenant_id":"tenant-a"}')"
}

bogus_tenant_key() {
  printf '%s-%s-%s' not a real-key
}

curl_ingest() {
  local tenant_key="$1" payload="$2"
  local tenant_header="X-Tenant-Key: ${tenant_key}"
  curl -s -X POST "$API/v1/traces" -H "$tenant_header" -H 'content-type: application/json' -d "$payload"
}

curl_put_traces() {
  local tenant_key="$1"
  local tenant_header="X-Tenant-Key: ${tenant_key}"
  hit -X PUT "$API/v1/traces" -H "$tenant_header" -d '{}'
}

echo "== Unauthenticated / hostile-input =="
check "A2 read no token 401"    "401" "$(hit "$API/v1/traces" | grep -o '[0-9]*$')"
check "A5 ingest no key 401"    '"code": "unauthorized"' "$(curl -s -X POST "$API/v1/traces" -H 'content-type: application/json' -d '{"spans":[]}')"
check "A6 bogus key fail-closed" '"code": "unauthorized"' "$(curl_ingest "$(bogus_tenant_key)" '{"spans":[{"trace_id":"aaaaaaaaaaaaaaaa","span_id":"1111111111111111","tenant_id":"tenant-a","kind":"llm","name":"x","status":"ok","start_time":"2026-08-18T18:00:00Z","end_time":"2026-08-18T18:00:01Z","prompt_preview":"ssn 123-45-6789"}]}')"
check "A8 forged unsigned JWT 401" "401" "$(hit "$API/v1/traces" -H "Authorization: Bearer $(forge_unsigned_jwt)" | grep -o '[0-9]*$')"
_wrong_method_key=x
check "A9 wrong method 404"     "404" "$(curl_put_traces "$_wrong_method_key" | grep -o '[0-9]*$')"
check "A13 edge HSTS present"   "max-age" "$(curl -s -D - -o /dev/null "$EDGE/health" | grep -i strict-transport)"

echo "== Authenticated (skipped unless creds exported) =="
if [ -n "${TENANT_B_JWT:-}" ]; then
  body=$(curl -s "$API/v1/traces/$TRACE_A" -H "Authorization: Bearer $TENANT_B_JWT")
  check "B1 cross-tenant read 403 body" '"code":"forbidden"' "$body"
  check "B1 no spans leaked" '^((?!spans).)*$' "$(printf '%s' "$body" | grep -c spans | sed 's/^0$/none/')"
else echo "  SKIP  B1 cross-tenant (set TENANT_B_JWT)"; fi

if [ -n "${TENANT_A_KEY:-}" ]; then
  flight='{"spans":[{"trace_id":"redteamaaaaaaaaaaaaaaaaaaaaaaaa","span_id":"1111111111111111","tenant_id":"tenant-a","kind":"llm","name":"demo.converse","status":"ok","start_time":"2026-08-22T12:00:00Z","end_time":"2026-08-22T12:00:01Z","cost_usd":0.002,"prompt_preview":"reach me at victim@example.com ssn 123-45-6789"}]}'
  resp=$(curl_ingest "$TENANT_A_KEY" "$flight")
  check "B2 ingest accepted 202" '"accepted":true' "$resp"
  if [ -n "${TENANT_A_JWT:-}" ]; then
    got=$(curl -s "$API/v1/traces/redteamaaaaaaaaaaaaaaaaaaaaaaaa" -H "Authorization: Bearer $TENANT_A_JWT")
    check "B2 masked at read" "\[SSN\]" "$got"
    check "B2 no raw SSN at read" '^((?!123-45-6789).)*$' "$(printf '%s' "$got" | grep -c 123-45-6789 | sed 's/^0$/clean/')"
  fi
else echo "  SKIP  B2 live PII flight (set TENANT_A_KEY [+ TENANT_A_JWT])"; fi

echo "== $pass passed, $fail failed =="
[ "$fail" -eq 0 ]
