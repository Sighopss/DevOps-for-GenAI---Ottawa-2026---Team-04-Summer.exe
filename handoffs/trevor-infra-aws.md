# Handoff — trevor-infra — aws

- Date: 2026-08-21
- Human: Trevor
- Agent id: trevor-infra
- Branch: trevor/infra/aws
- PR: TBD
- Mission file: `skills/trevor-recorder/agents/infra.md`

Closes #10. Remote-state bootstrap is issue #5 — mention only, **do not close #5**.

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
infra/
handoffs/trevor-infra-aws.md
```

## Do not touch

```
vault/
web/
sdk/
demo-app/
scripts/
.github/
Makefile
PRODUCT.md
DESIGN.md
contracts/
```

## Safe to run in parallel with

`trevor-sdk`, `trevor-ci`, `trevor-demo`, `trevor-scripts`, Alexis `vault/**`, Michael `web/**`.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Build`
- P-ids this PR moves: `P-05`, `P-07`, `P-13` (also ships pieces of `P-10` logs/alarm and `P-11` tfvars.example)
- Rubric rows (pts): `Security 15`, `DevOps 10`
- Tests / attack shown: `terraform fmt`; `terraform init -backend=false && terraform validate` (no apply). IAM has no `s3:*` / `dynamodb:*` / `bedrock:*` on `*`. CORS origin is not `*`. Ingest is not Cognito. No MFA. No SSH.
- Stub/live (P-15): Lambda zip is the 501 stub until Alexis lands `vault/`. KMS, WAF, Cognito, OIDC, CloudFront, HTTP API are live **after** a human-approved apply (not this PR).

## What I shipped

- files: `infra/**` (Terraform HTTP API, Cognito, two Lambdas, KMS, OAC, WAF, OIDC, secrets placeholders, CloudWatch 7d + 5xx alarm) and this handoff
- outputs / env **names** (no secret values): `ingest_url`, `api_url`, `cloudfront_url`, `cloudfront_distribution_id`, `user_pool_id`, `user_pool_client_id`, `cognito_domain`, `table_name`, `payload_bucket`, `web_bucket`, `oidc_role_arn`; Michael `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_DOMAIN`; SDK `TRACEVAULT_INGEST_URL`
- tests: terraform validate

## What I need

- from whom: Human (issue **#5** remote-state bootstrap + first apply); Alexis (`vault/` handlers so the stub 501 goes away); Michael (wire `NEXT_PUBLIC_*` from outputs); trevor-ci (`deploy.yml` assuming `oidc_role_arn`)
- contract / URL / header / path: `POST /v1/traces` + `X-Tenant-Key`; `GET /v1/traces*` + Cognito ID token; `GET /health` no auth; CORS origin = CloudFront URL

## Blocked on

`Human` for remote state (#5, **do not close #5** from this PR) and approved `terraform apply`. Alexis for real handlers. Does not close CI (#6) or public URL (#11).

## Contract reminder

Trevor owns AWS wiring. Alexis owns redact/store/read JSON. Michael owns `web/`. Ingest is not Cognito. Grafana is not the UI.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
