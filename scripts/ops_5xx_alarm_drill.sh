#!/usr/bin/env bash
# #50 — drive the API 5xx alarm into ALARM, then wait for OK.
# Safe default: PutMetricData against the same metric the alarm watches
# (AWS/ApiGateway 5xx). That proves the alarm path without abusing tenants.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"
ALARM_NAME="${ALARM_NAME:-tracevault-dev-api-5xx}"

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI missing" >&2
  exit 2
fi

if [[ -z "${API_ID:-}" ]] && [[ -d "$ROOT/infra" ]] && command -v terraform >/dev/null 2>&1; then
  API_URL="$(terraform -chdir="$ROOT/infra" output -raw api_url 2>/dev/null || true)"
  # https://{api-id}.execute-api.{region}.amazonaws.com → api-id
  if [[ -n "$API_URL" ]]; then
    API_ID="$(printf '%s' "$API_URL" | sed -E 's|https://([^.]+)\.execute-api\..*|\1|')"
  fi
fi

STAGE="${STAGE:-\$default}"

if [[ -z "${API_ID:-}" ]]; then
  echo "Set API_ID (HTTP API id) or provide terraform output api_url." >&2
  echo "Example: API_ID=abc123 bash scripts/ops_5xx_alarm_drill.sh" >&2
  exit 2
fi

echo "baseline:"
aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
  --query 'MetricAlarms[0].{State:StateValue,Updated:StateUpdatedTimestamp,Reason:StateReason}' \
  --output table

echo "publishing synthetic 5xx=6 for ApiId=${API_ID} Stage=${STAGE}…"
aws cloudwatch put-metric-data \
  --region "$REGION" \
  --namespace AWS/ApiGateway \
  --metric-data "[
    {\"MetricName\":\"5xx\",\"Dimensions\":[{\"Name\":\"ApiId\",\"Value\":\"${API_ID}\"},{\"Name\":\"Stage\",\"Value\":\"${STAGE}\"}],\"Value\":6,\"Unit\":\"Count\"}
  ]"

echo "waiting up to 7 minutes for ALARM…"
deadline=$((SECONDS + 420))
state=""
while (( SECONDS < deadline )); do
  state="$(aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
    --query 'MetricAlarms[0].StateValue' --output text)"
  echo "  state=$state"
  if [[ "$state" == "ALARM" ]]; then
    break
  fi
  sleep 30
done

if [[ "$state" != "ALARM" ]]; then
  echo "FAIL: alarm did not enter ALARM (last state=$state)" >&2
  exit 1
fi

echo "ALARM observed. Waiting for return to OK (treat_missing_data=notBreaching)…"
deadline=$((SECONDS + 420))
while (( SECONDS < deadline )); do
  state="$(aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
    --query 'MetricAlarms[0].StateValue' --output text)"
  echo "  state=$state"
  if [[ "$state" == "OK" ]]; then
    echo "OK: alarm recovered"
    aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
      --query 'MetricAlarms[0].{State:StateValue,Updated:StateUpdatedTimestamp,Reason:StateReason}' \
      --output table
    exit 0
  fi
  sleep 30
done

echo "WARN: ALARM seen but OK not observed within window — capture console screenshot." >&2
exit 0
