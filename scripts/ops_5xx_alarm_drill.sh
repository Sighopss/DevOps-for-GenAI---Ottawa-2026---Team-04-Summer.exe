#!/usr/bin/env bash
# #50 — exercise the API 5xx alarm into ALARM, then back to OK.
#
# AWS rejects PutMetricData into the AWS/ApiGateway namespace (reserved).
# This drill therefore uses SetAlarmState to prove the alarm object can
# transition ALARM → OK, then clears with a real describe. Labelled honestly
# as an alarm-control drill, not a forged ApiGateway metric.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ALARM_NAME="${ALARM_NAME:-tracevault-dev-api-5xx}"

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI missing" >&2
  exit 2
fi

echo "baseline:"
aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
  --query 'MetricAlarms[0].{State:StateValue,Updated:StateUpdatedTimestamp,Reason:StateReason}' \
  --output table

echo "forcing ALARM via SetAlarmState (ApiGateway namespace is not writable by PutMetricData)…"
aws cloudwatch set-alarm-state \
  --region "$REGION" \
  --alarm-name "$ALARM_NAME" \
  --state-value ALARM \
  --state-reason "TraceVault #50 ops drill $(date -u +%Y-%m-%dT%H:%M:%SZ): operator forced ALARM to prove alarm path"

sleep 2
state="$(aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
  --query 'MetricAlarms[0].StateValue' --output text)"
echo "  state=$state"
if [[ "$state" != "ALARM" ]]; then
  echo "FAIL: expected ALARM, got $state" >&2
  exit 1
fi

echo "forcing OK (clear)…"
aws cloudwatch set-alarm-state \
  --region "$REGION" \
  --alarm-name "$ALARM_NAME" \
  --state-value OK \
  --state-reason "TraceVault #50 ops drill $(date -u +%Y-%m-%dT%H:%M:%SZ): operator cleared ALARM after path proof"

sleep 2
aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
  --query 'MetricAlarms[0].{State:StateValue,Updated:StateUpdatedTimestamp,Reason:StateReason}' \
  --output table

final="$(aws cloudwatch describe-alarms --region "$REGION" --alarm-names "$ALARM_NAME" \
  --query 'MetricAlarms[0].StateValue' --output text)"
if [[ "$final" != "OK" ]]; then
  echo "FAIL: expected OK after clear, got $final" >&2
  exit 1
fi

echo "OK: alarm path ALARM → OK proven for $ALARM_NAME"
