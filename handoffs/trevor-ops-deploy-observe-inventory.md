# Handoff — trevor-ops — deploy-observe-inventory (#49 #50 #55)

- Date: 2026-08-22
- Human: Trevor
- Agent id: trevor-ops
- Branch: `trevor/ops/deploy-observe-inventory`
- Related: #49, #50, #55 (closes Trevor halves); absorbs Alexis #117 inventory rows already on `main`

## Claimed paths

```
README.md
.gitignore
Makefile
docs/DEPLOY_GATE.md
docs/OBSERVABILITY.md
scripts/demo_ingest_down.sh
scripts/ops_5xx_alarm_drill.sh
sdk/src/tracevault/client.py
sdk/tests/test_unreachable_ingest.py
handoffs/trevor-ops-deploy-observe-inventory.md
```

## Do not touch

```
vault/                          (Alexis)
web/ PRODUCT.md DESIGN.md       (Michael)
infra/*.tf                      (no Terraform edits this PR — prod GH Environment only)
```

## What shipped

### #49 Deploy gate
- GitHub Environment **`prod`** created with required reviewer `Sighopss` + protected-branch policy (API).
- Rollback drill executed: re-ran last previously-green `deploy.yml` [run 32585304984](https://github.com/Sighopss/DevOps-for-GenAI---Ottawa-2026---Team-04-Summer.exe/actions/runs/32585304984); apply failed because that SHA predates tenant-password secrets — recorded honestly in `docs/DEPLOY_GATE.md`.
- SDK: unreachable ingest (network) now writes `sdk/.last-flight.json` instead of raising (`status_code == 0`).
- Scripted failure demo: `scripts/demo_ingest_down.sh` + unit test `sdk/tests/test_unreachable_ingest.py`.

### #50 Observability pack
- `docs/OBSERVABILITY.md` — where traces/metrics/logs/health/audit live + operator commands.
- `/health` proven live → `{"ok":true}`.
- `scripts/ops_5xx_alarm_drill.sh` ready; live ALARM→OK still needs operator AWS SSO (token expired on this machine).
- `make help` points at both evidence docs.

### #55 Technology inventory
- Trevor rows + assembly under README **Technology inventory** (Alexis vault rows already on `main` via #117).
- Recorder/edge limitations + roadmap under **Limitations** (TLS floor, WAF, red deploy, unpublished Explorer, SDK fallback).

## Verification

```text
cd sdk && uv run pytest -q   # includes test_unreachable_ingest
# demo (Git Bash): bash scripts/demo_ingest_down.sh
curl https://55qm437628.execute-api.us-east-1.amazonaws.com/health   # {"ok":true}
gh api repos/.../environments/prod   # required_reviewers includes Sighopss
```

## Blocked on / follow-ups

- Operator AWS SSO to run `scripts/ops_5xx_alarm_drill.sh` and a live `demo_pii_flight.sh` with tenant key (#50 remaining checkboxes).
- Restore a green `deploy.yml` on current `main` so rollback has a safe modern target (#49 lesson).
- Close #117 if still open (already merged as `fbda054`).
