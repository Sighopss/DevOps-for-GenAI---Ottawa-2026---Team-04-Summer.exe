# Observability evidence pack (#50)

Handbook P-10 + §2 **Operate**. Lead: Trevor. Vault half: Alexis. Explorer: Michael.

Where each signal lives, how to prove it, and what we have already proven.

## Map — where to look

| Signal | Where | How to prove |
|---|---|---|
| Traces (product) | DynamoDB `tracevault-dev-traces` + S3 `tracevault-dev-payloads-…` via `GET /v1/traces*` / Explorer | Live `scripts/demo_pii_flight.sh` with ingest URL + tenant key → flight visible under `tenant-a` |
| Metrics / 5xx alarm | CloudWatch alarm `tracevault-dev-api-5xx` (`infra/cloudwatch.tf`) | [`scripts/ops_5xx_alarm_drill.sh`](../scripts/ops_5xx_alarm_drill.sh) — `SetAlarmState` ALARM → OK (ApiGateway namespace is not writable via `PutMetricData`) |
| Logs | `/aws/lambda/tracevault-dev-vault-ingest`, `/aws/lambda/tracevault-dev-vault-read` (7d retention) | Spot-check: no raw email/SSN after a `--pii` flight |
| Health | `GET {api_url}/health` → `200 {"ok":true}` (no Lambda) | `curl -sS "$API_URL/health"` |
| Audit trail | Dynamo audit rows on trace open | Open a trace as `tenant-a`; confirm audit row (Explorer / vault read path) |
| Runbook | `make help` + this file + [`DEPLOY_GATE.md`](DEPLOY_GATE.md) | Second person can find each row without Slack archaeology |

`api_url` (live): `https://55qm437628.execute-api.us-east-1.amazonaws.com`  
(`terraform -chdir=infra output -raw api_url` when state is local.)

## Proven 2026-08-22 (profile `tracevault`)

| Item | Status | Evidence |
|---|---|---|
| `/health` reachable | **Yes** | `curl https://55qm437628.execute-api.us-east-1.amazonaws.com/health` → `{"ok":true}` |
| Runbook pointers | **Yes** | `make help` (Health, Rollback, CloudWatch log groups); this file |
| 5xx alarm **exists** | **Yes** | `tracevault-dev-api-5xx` in CloudWatch (`AWS/ApiGateway` / `5xx`), state was `OK` |
| 5xx alarm **ALARM → OK** | **Yes** | 2026-08-22 ~19:24Z UTC: `SetAlarmState` → `ALARM` (reason: `#50 ops drill … forced ALARM`) then `OK` (reason: `… cleared ALARM after path proof`). Script: `scripts/ops_5xx_alarm_drill.sh`. Honest caveat: AWS rejects `PutMetricData` into `AWS/*` namespaces, so this is an alarm-control drill, not a forged ApiGateway datapoint. |
| Live PII flight → stored trace | **Yes** | `TRACEVAULT_FAKE_BEDROCK=1 bash scripts/demo_pii_flight.sh` with Secrets Manager `tracevault-dev/ingest/tenant-a` → `POST /v1/traces` **202 Accepted**. Trace id `b352dbfcb3259b6378736aeeb274ae2f`. S3 object `s3://tracevault-dev-payloads-887991000498/tenant-a/b352dbfc…/3dd160ca….json` (1720 B, 2026-08-22 15:23 ET). |
| At-rest redaction | **Yes** | Stored `prompt_preview`: `Contact [EMAIL] SSN [SSN]. What is retention?` — no raw `@`, `example.com`, or `123-45-6789` in the payload. |
| Log spot-check (no raw PII) | **Yes** | `filter-log-events` on `/aws/lambda/tracevault-dev-vault-ingest` (last 20 min) for `example.com` and `123-45-6789` → **0** events. Ingest request `36480a38-005e-4012-8370-4e0bca56c2d4` completed ~1904 ms. |
| Audit row on open | **Pending Explorer** | Needs Cognito session + Explorer open (Michael). Vault write path for audit is Alexis. |

## Operator commands (copy/paste)

```bash
export AWS_PROFILE=tracevault
export AWS_REGION=us-east-1
API_URL=https://55qm437628.execute-api.us-east-1.amazonaws.com

curl -sS "$API_URL/health"

aws logs describe-log-groups --log-group-name-prefix /aws/lambda/tracevault-dev-vault --region us-east-1
aws cloudwatch describe-alarms --alarm-names tracevault-dev-api-5xx --region us-east-1

bash scripts/ops_5xx_alarm_drill.sh

# Live flight (key from Secrets Manager — never commit)
export TRACEVAULT_INGEST_URL="$API_URL"
export TRACEVAULT_TENANT_KEY="$(aws secretsmanager get-secret-value \
  --secret-id tracevault-dev/ingest/tenant-a --query SecretString --output text \
  | python -c 'import sys,json; print(json.load(sys.stdin)["key"])')"
export TRACEVAULT_FAKE_BEDROCK=1
bash scripts/demo_pii_flight.sh
```

## Split of ownership

- **Trevor:** alarm + health + deploy/rollback evidence, log group names in the runbook, this pack’s assembly, live flight + log/S3 spot-check above.
- **Alexis:** at-rest / redaction semantics (confirmed live above); audit row schema.
- **Michael:** Explorer surfaces that make the same flight and audit trail visible to a judge without the AWS console.
