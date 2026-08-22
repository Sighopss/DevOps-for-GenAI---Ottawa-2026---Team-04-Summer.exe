# Handoff — trevor-ci — gha-makefile

- Date: 2026-08-21
- Human: Trevor
- Agent id: trevor-ci
- Branch: trevor/ci/gha-makefile
- PR: TBD
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
- Stub/live (P-15): Workflows are live GitHub Actions. `terraform apply`, S3 sync, and CloudFront invalidate stay skipped until `infra/` exists and secret `AWS_ROLE_ARN` is set (OIDC). No Bedrock, no live URL in this PR.

## What I shipped

- files:
  - `Makefile` (Unix; `help` is the runbook: `GET /health`, Cognito `tenant-a`/`tenant-b`, rollback = re-run last green `deploy.yml`, CloudWatch `/aws/lambda/vault-ingest` + `vault-read` 7d)
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
- outputs / env **names** (no secret values):
  - `TRACEVAULT_INGEST_URL` (health curl in Makefile help)
  - `AWS_ROLE_ARN` (GitHub Actions secret — OIDC role to assume)
  - `GITLEAKS_LICENSE` (orgs only)
  - `AWS_REGION=us-east-1`
  - GitHub Environments `dev` and `prod` (prod expected to require a reviewer)
- tests:
  - gitleaks + trivy run on this PR (empty tree)
  - `make help` / `make test` / `make vault` / `make web` / `make demo` / `make plan` / `make sbom` skip missing dirs

## What I need

- from whom: Human Trevor
- contract / URL / header / path: GitHub Environment `prod` protection; required checks on `main`; OIDC provider + `AWS_ROLE_ARN` secret (Trevor 1). Alexis pytest under `vault/` once that tree exists. Michael `pnpm lint` + Playwright once `web/` exists. `trevor-infra` terraform outputs `web_bucket` and `cloudfront_distribution_id` for the sync step.

## Blocked on

Human Trevor (OIDC role + Environments). `trevor-infra` before apply actually mutates AWS. Nobody for merge of this PR except Trevor.

## Contract reminder

CI does not invent HTTP routes. Health is `GET /health` → `200 {"ok":true}`. Deploy is `main` only. Ingest stays `X-Tenant-Key`; reads stay Cognito JWT. This PR owns workflow YAML and the Makefile runbook only.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
