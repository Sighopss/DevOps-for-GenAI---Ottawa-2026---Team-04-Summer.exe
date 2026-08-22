# Deploy gate — rollback, approval, failure demo (#49)

Handbook §2 **Deploy** gate + judge **Failure handling**. Owner: Trevor.

## Approval path (real)

| Environment | Protection | Evidence |
|---|---|---|
| `dev` | GitHub Environment `dev` on `deploy.yml` → `terraform-apply-dev` | Exists; auto-apply on `main` |
| `prod` | GitHub Environment `prod` with **required reviewers** + protected-branch deploy policy | Created 2026-08-22: required reviewer [`Sighopss`](https://github.com/Sighopss). Job `terraform-apply-prod` cannot apply until that review is approved. |

Repo → Settings → Environments → **prod** → Required reviewers: `Sighopss`.  
`.github/workflows/deploy.yml` already sets `environment: prod` on the prod apply job — the protection is no longer documentation-only.

## Rollback procedure

Rollback = **re-run the last green** `deploy.yml` on `main`:

Actions → `deploy.yml` → last successful run → **Re-run all jobs**.

Do not `terraform apply` from a feature branch. No CodePipeline. No SSH.

```bash
gh run list --workflow=deploy.yml --branch main --limit 20
gh run rerun <RUN_ID>
```

## Rollback drill (executed 2026-08-22)

| Field | Value |
|---|---|
| When | 2026-08-22 ~18:59 UTC |
| What we re-ran | Last previously-green `deploy.yml`: [run 32585304984](https://github.com/Sighopss/DevOps-for-GenAI---Ottawa-2026---Team-04-Summer.exe/actions/runs/32585304984) (merge #88 / explorer fixtures) |
| What broke | `terraform-apply-dev` exited in ~8s: that SHA predates required `TF_VAR_tenant_*_password` wiring and the OIDC secret placeholders now expected by `deploy.yml`. `web-sync` then failed (no Terraform outputs from the aborted apply). |
| Recovery | Do **not** force an ancient green onto current state. Recovery = deploy **current** `main` (with tenant password secrets present) or re-run the newest intentional green. Recognition time: <2 minutes after the failed job. |
| Lesson for the demo | The rollback **control** works (re-run last green). The drill also proved that **last-green is only safe while the workflow contract matches live secrets/state** — say that out loud; do not claim a green re-run that was not green. |

## Graceful-degradation demo (ingest unreachable)

Script: [`scripts/demo_ingest_down.sh`](../scripts/demo_ingest_down.sh).

1. Point the SDK at a blackhole ingest URL (or leave it unset).
2. Run one demo flight with `TRACEVAULT_FAKE_BEDROCK=1`.
3. Process exits **0**; spans land in `sdk/.last-flight.json` (fallback only — not the product).

Presentation line: *“If ingest is down, the recorder still finishes the request and parks the flight locally. We lose central observability for that call; we do not crash the user request or print raw prompts.”*

## Failure demo (scripted for the stage)

| Step | Command | Expect |
|---|---|---|
| 1 | `bash scripts/demo_ingest_down.sh` | Exit 0; prints path to `sdk/.last-flight.json` |
| 2 | `test -f sdk/.last-flight.json && python -c "import json;print(len(json.load(open('sdk/.last-flight.json'))))"` | Span count ≥ 1 |
| 3 | Narrate contrast | With `TRACEVAULT_INGEST_URL` set + tenant key → live `POST /v1/traces`; with it unreachable → local fallback, no crash |

Optional live contrast (needs tenant key): `make demo` with ingest URL set → flight in the vault instead of the local file.
