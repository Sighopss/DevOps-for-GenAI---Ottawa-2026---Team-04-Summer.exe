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
- Judge bar (`JUDGE.md`): never-kill intact across the five items this stack owns. **CORS = CloudFront only** — `allow_origins = [local.web_origin]` (`https://<distribution>`), never `*`; methods `GET,POST,OPTIONS`, headers `Authorization,Content-Type,X-Tenant-Key`, credentials off. **JWT `custom:tenant_id`** — the pool schema defines `tenant_id`, both users carry `custom:tenant_id`, and the v2 JWT authorizer guards all three `GET /v1/traces*` routes; the claim-vs-stored-tenant compare that yields **403 not 404** is Alexis's `vault-read` — API Gateway only proves the token is real. **HTTPS URL** — CloudFront `redirect-to-https`, TLS 1.2_2021 minimum, HSTS preload, and the web bucket denies `aws:SecureTransport=false`. **`/health`** — no Lambda: an `HTTP_PROXY` route to `health.json` (`{"ok":true}`, `application/json`, `aws_s3_object.health`) on the CloudFront origin, per the amended `contracts/http.md`; the amendment's cost is that `/health` now depends on CloudFront and that object existing. **Ingest key ≠ user JWT** — `POST /v1/traces` is `authorization_type = "NONE"` with the key held per tenant in Secrets Manager under the CMK; no Cognito on the ingest path. Two notes for Trevor, neither a break in this stack: (1) CloudFront rewrites **origin** 403/404 to `/index.html` for SPA routing, but the tenant-mismatch 403 comes from the execute-api domain and does not pass through the distribution, so the judged 403 is untouched; (2) `contracts/http.md` says "access token" for `GET /v1/traces*` while `custom:tenant_id` only ever rides the **ID** token — see Contract reminder.

## What I shipped

- files: `infra/**` (Terraform HTTP API, Cognito, two Lambdas, KMS, OAC, WAF, OIDC, secrets placeholders, CloudWatch 7d + 5xx alarm) and this handoff
- outputs / env **names** (no secret values): `ingest_url`, `api_url`, `cloudfront_url`, `cloudfront_distribution_id`, `user_pool_id`, `user_pool_client_id`, `cognito_domain`, `table_name`, `payload_bucket`, `web_bucket`, `oidc_role_arn`; Michael `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_DOMAIN`; SDK `TRACEVAULT_INGEST_URL`
- tests: terraform validate

## What I need

- from whom: Human (issue **#5** remote-state bootstrap + first apply); Alexis (`vault/` handlers so the stub 501 goes away); Michael (wire `NEXT_PUBLIC_*` from outputs); trevor-ci (`deploy.yml` assuming `oidc_role_arn`)
- contract / URL / header / path: `POST /v1/traces` + `X-Tenant-Key`; `GET /v1/traces*` + Cognito ID token (see Contract reminder); `GET /health` no auth, no Lambda, `HTTP_PROXY` → `health.json` on the CloudFront origin; CORS origin = CloudFront URL

## Blocked on

`Human` for remote state (#5, **do not close #5** from this PR) and approved `terraform apply`. Alexis for real handlers. Does not close CI (#6) or public URL (#11).

## Contract reminder

Trevor owns AWS wiring. Alexis owns redact/store/read JSON. Michael owns `web/`. Ingest is not Cognito. Grafana is not the UI.

Two things to read against the amended `contracts/http.md` (PR #26):

1. `/health` is **not** an API Gateway mock. HTTP API v2 has no `MOCK` integration type (WebSocket only), so `infra/api.tf` implements the route as `HTTP_PROXY` to a static `health.json` on the CloudFront origin. Still no Lambda, still `200 {"ok":true}`. Cost: `/health` is only green while CloudFront and that object are up.
2. Token type is **unsettled and needs Trevor**: `http.md` says `GET /v1/traces*` carries a Cognito **access** token; this stack and `infra/README.md` tell Michael to send the **ID** token, because Cognito puts `custom:tenant_id` on the ID token only. The v2 JWT authorizer accepts either (it matches `aud` or `client_id`), so the mismatch would not fail at the gateway — it would surface as a missing `custom:tenant_id` in Alexis's `vault-read`. Pick one before the demo.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
