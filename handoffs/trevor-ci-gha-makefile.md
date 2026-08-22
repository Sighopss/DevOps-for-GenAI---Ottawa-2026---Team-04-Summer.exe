# Handoff — trevor-ci — gha-makefile

- Date: 2026-08-21
- Human: Trevor
- Agent id: trevor-ci
- Branch: trevor/ci/gha-makefile
- PR: 27
- Mission file: `skills/trevor-recorder/agents/ci.md`

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
.github/
Makefile
.gitignore
handoffs/trevor-ci-gha-makefile.md
```

## Do not touch

```
sdk/
demo-app/
infra/
scripts/
vault/
web/
contracts/
PRODUCT.md
DESIGN.md
assets/
PLAN.md
skills/
```

## Safe to run in parallel with

`trevor-sdk`, `trevor-demo`, `trevor-scripts`, `trevor-infra`, Alexis vault missions, Michael web/PRODUCT missions — none of those prefixes overlap this PR.

## Handbook evidence (required — 2026 workbook)

Empty = incomplete PR. Copy from PLAN **Rubric 100** / P-ids.

- Lifecycle stage: Build / Validate
- P-ids this PR moves: P-05, P-13, P-14
- Rubric rows (pts): DevOps 10, Security 15
- Tests / attack shown: gitleaks fail-closed on every PR and `main`; `trivy fs` on every PR with CycloneDX artifact (not committed); path jobs (`sdk.yml` / `vault.yml` / `web.yml` / `infra.yml`) skip when those directories are missing; `deploy.yml` is `main`-only and will not `terraform apply` on an empty tree.
- Stub/live (P-15): Workflows are live GitHub Actions. `terraform apply`, S3 sync, and CloudFront invalidate stay skipped until `infra/` exists and secret `AWS_ROLE_ARN` is set (OIDC). No Bedrock, no live URL in this PR. `make help` prints a runbook, not a health check it has run — nobody has curled a real `/health` yet because the stack is not applied.
- Judge bar (`JUDGE.md`): never-kill still intact. This PR ships CI YAML and the Makefile runbook only — it writes no application code, so redaction, 403-not-404, the HTTPS URL, the Day 1 fixture UI, CORS = CloudFront only, JWT `custom:tenant_id`, the single retrieve tool, and ingest-key ≠ user-JWT are all untouched. The one never-kill this PR speaks to is `/health`: the runbook previously claimed an API Gateway mock, which HTTP API v2 does not support, so a judge following it would have described a mechanism that does not exist. It now matches locked `contracts/http.md` and `infra/api.tf` (HTTP_PROXY → `health.json` on the CloudFront origin, no Lambda, still `200 {"ok":true}`). Nothing named broken; no owner needed.

## What I shipped

- files:
  - `Makefile` (Unix; `help` is the runbook: `GET /health`, Cognito `tenant-a`/`tenant-b`, rollback = re-run last green `deploy.yml`, CloudWatch `/aws/lambda/tracevault-{env}-vault-{ingest,read}` 7d)
  - `.gitignore` (Python, Terraform, env, worktrees, `sbom.cdx.json`)
  - `.github/CODEOWNERS` (ownership.md path fences; `@Sighopss` only — `@trevor`/`@alexis`/`@michael` are not GitHub accounts here)
  - `.github/pull_request_template.md`
  - `.github/workflows/gitleaks.yml`
  - `.github/workflows/trivy.yml`
  - `.github/workflows/sdk.yml`
  - `.github/workflows/vault.yml`
  - `.github/workflows/web.yml`
  - `.github/workflows/infra.yml`
  - `.github/workflows/deploy.yml`
  - `handoffs/trevor-ci-gha-makefile.md`
- runbook correction in `make help`, checked line by line against locked `contracts/http.md` and `infra/` on `trevor/infra/aws`:
  - `/health` is **not** an API Gateway mock. HTTP API (API Gateway v2) supports `MOCK` integrations on WebSocket APIs only, so `infra/api.tf` routes `GET /health` as `HTTP_PROXY` to the static `health.json` object on the CloudFront origin (`aws_s3_object.health` in `infra/storage.tf`). Still no Lambda, still `200 {"ok":true}` — only the mechanism changed, and the runbook now says so.
  - Health curl now builds on the `api_url` infra output (HTTP API base URL), not `TRACEVAULT_INGEST_URL`. The `ingest_url` output already ends in `/v1/traces`, so it was never the right base for `/health`.
  - CloudWatch group names corrected to the `{project}-{env}` prefix the Terraform actually creates (`/aws/lambda/tracevault-dev-vault-ingest`, `-vault-read`); the old runbook names had no prefix and would not have been found in the console. Also notes that `/health` has no log group, because it never reaches a Lambda.
  - Cognito block now names `TF_VAR_tenant_a_password` / `TF_VAR_tenant_b_password` (names only, no values) and records that ingest uses `X-Tenant-Key` and is never a user JWT.
  - No new targets, no restructuring: the target list, rollback block, and `.PHONY` are unchanged.
- CI guard for `scripts/check_unix.sh`: `.github/workflows/trivy.yml` runs it immediately after checkout, before the SBOM and scan steps. `trivy.yml` has no path filter, so the guard runs on every PR. It is wrapped in `if [ -f scripts/check_unix.sh ]` and otherwise prints `skip: scripts/check_unix.sh missing (greenfield)`, so the job stays green on an empty tree and while `scripts/` is still an open PR on another lane. `scripts/` itself is not edited here. It is deliberately not in `gitleaks.yml`: that job stays single-purpose so a red gitleaks run always means a secret, never a missing `awk`.
- outputs / env **names** (no secret values):
  - `api_url` (infra output — HTTP API base URL; the health curl in `make help` builds on it)
  - `TRACEVAULT_INGEST_URL` (SDK/demo ingest base — named in `make help` only to say it is *not* the health URL)
  - `AWS_ROLE_ARN` (GitHub Actions secret — OIDC role to assume)
  - `GITLEAKS_LICENSE` (orgs only)
  - `AWS_REGION=us-east-1`
  - GitHub Environments `dev` and `prod` (prod expected to require a reviewer)
- tests:
  - gitleaks + trivy run on this PR (empty tree)
  - `make help` / `make test` / `make vault` / `make web` / `make demo` / `make plan` / `make sbom` skip missing dirs
  - every workflow in `.github/workflows/` parsed as YAML (`yaml` npm parser, strict mode, zero errors) — `make` and PyYAML are not installed on this box, so `make help` was verified by extracting the recipe and rendering it through `sh` with make's `$$` → `$` expansion applied

## What I need

- from whom: Human Trevor
- contract / URL / header / path: GitHub Environment `prod` protection; required checks on `main`; OIDC provider + `AWS_ROLE_ARN` secret (Trevor 1). Alexis pytest under `vault/` once that tree exists. Michael `pnpm lint` + Playwright once `web/` exists. `trevor-infra` terraform outputs `web_bucket` and `cloudfront_distribution_id` for the sync step.
- flagged, not mine to fix: `TRACEVAULT_INGEST_URL` means two different things across lanes. `sdk/src/tracevault/client.py` does `ingest_url.rstrip("/") + "/v1/traces"`, i.e. it expects a **base** URL, but the `ingest_url` terraform output is already `{api_endpoint}/v1/traces`. Wiring the output straight into the env var would POST to `/v1/traces/v1/traces`. Owners: `trevor-infra` and `trevor-sdk` — one of them should change. `make help` sidesteps it by using `api_url` for health.

## Blocked on

Human Trevor (OIDC role + Environments). `trevor-infra` before apply actually mutates AWS. Nobody for merge of this PR except Trevor.

## Contract reminder

CI does not invent HTTP routes. Health is `GET /health` → `200 {"ok":true}`, unauthenticated, no Lambda, served as an `HTTP_PROXY` route to `health.json` on the CloudFront origin. Deploy is `main` only. Ingest stays `X-Tenant-Key`; reads stay Cognito JWT. This PR owns workflow YAML and the Makefile runbook only.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
