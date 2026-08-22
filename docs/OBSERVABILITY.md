# Observability evidence pack (#50)

Handbook P-10 + §2 **Operate**. Lead: Trevor. Vault half: Alexis. Explorer: Michael.

Where each signal lives, how to prove it, and what we have already proven.

## Map — where to look

| Signal | Where | How to prove |
|---|---|---|
| Traces (product) | DynamoDB + S3 via `GET /v1/traces*` / Explorer | Live `scripts/demo_pii_flight.sh` with `TRACEVAULT_INGEST_URL` + tenant key → flight visible to `tenant-a` |
| Metrics / 5xx alarm | CloudWatch alarm `tracevault-dev-api-5xx` (`infra/cloudwatch.tf`) | [`scripts/ops_5xx_alarm_drill.sh`](../scripts/ops_5xx_alarm_drill.sh) — force ≥5 5xx, capture `ALARM` → `OK` |
| Logs | `/aws/lambda/tracevault-dev-vault-ingest`, `/aws/lambda/tracevault-dev-vault-read` (7d retention) | Spot-check: no raw email/SSN after a `--pii` flight |
| Health | `GET {api_url}/health` → `200 {"ok":true}` (no Lambda) | `curl -sS "$API_URL/health"` |
| Audit trail | Dynamo audit rows (`a#…`) on trace open | Open a trace as `tenant-a`; confirm audit row (depends on vault #16 / read path) |
| Runbook | `make help` + this file + [`DEPLOY_GATE.md`](DEPLOY_GATE.md) | Second person can find each row without Slack archaeology |

`api_url` comes from `terraform -chdir=infra output -raw api_url`. Do not hardcode.

## Proven in this pass (2026-08-22)

| Item | Status | Evidence |
|---|---|---|
| `/health` reachable | **Yes** | `curl https://55qm437628.execute-api.us-east-1.amazonaws.com/health` → `{"ok":true}` |
| Runbook pointers | **Yes** | `make help` (Health, Rollback, CloudWatch log groups); this file |
| 5xx alarm **exists** in Terraform | **Yes** | `aws_cloudwatch_metric_alarm.api_5xx` in `infra/cloudwatch.tf` (threshold 5 / 5 min) |
| 5xx alarm **state transition tested** | **Pending AWS creds** | Script ready: `scripts/ops_5xx_alarm_drill.sh` — needs operator SSO + API id |
| Live PII flight → visible trace | **Pending tenant key** | `scripts/demo_pii_flight.sh` — needs `TRACEVAULT_INGEST_URL` + `TRACEVAULT_TENANT_KEY` (Secrets Manager; not in git) |
| Log spot-check (no raw PII) | **Pending** after live flight | `aws logs filter-log-events …` against ingest/read groups |
| Audit row on open | **Pending** Explorer publish + Cognito session | Michael Explorer + Alexis audit path |

## Operator commands (copy/paste)

```bash
# Health
API_URL="$(terraform -chdir=infra output -raw api_url)"
curl -sS "$API_URL/health"

# Log groups (us-east-1, retention 7d)
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/tracevault-dev-vault --region us-east-1

# Alarm
aws cloudwatch describe-alarms --alarm-names tracevault-dev-api-5xx --region us-east-1

# 5xx drill (deliberate — see script header)
bash scripts/ops_5xx_alarm_drill.sh
```

## Split of ownership

- **Trevor:** alarm + health + deploy/rollback evidence, log group names in the runbook, this pack’s assembly.
- **Alexis:** at-rest / redaction proof that a live flight stored no raw PII; audit row semantics.
- **Michael:** Explorer surfaces that make the same flight and audit trail visible to a judge without the AWS console.
