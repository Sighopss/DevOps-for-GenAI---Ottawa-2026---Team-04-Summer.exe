# Handoff — trevor-infra — cognito-explorer-callback

- Date: 2026-08-22
- Human: Trevor
- Agent id: trevor-infra
- Branch: `trevor/infra/cognito-explorer-callback`
- PR: TBD
- Mission / scope: Allowlist Cognito Hosted UI callback/logout URLs for `${web_origin}/explorer/` (post-#139 welcome sign-in), keep bare CloudFront origin, and make token exchange use the same `redirect_uri` as authorize.

## Claimed paths (collision)

```
infra/cognito.tf
web/src/lib/cognito.ts
web/tests/explorer.spec.ts
handoffs/trevor-infra-cognito-explorer-callback.md
```

## Do not touch

```
vault/
sdk/
infra/cloudfront.tf
infra/api.tf
.github/workflows/
```

## Safe to run in parallel with

Michael web/CSP work that does not edit `cognito.ts` / explorer OAuth tests. Alexis vault lanes. Trevor docs PRs that stay out of `infra/cognito.tf`.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Operate`
- P-ids this PR moves: `P-15` (live Explorer sign-in), Hosted UI handoff after #139
- Rubric rows (pts): Security (Cognito redirect allowlist), DevOps (Terraform drift)
- Tests / attack shown: Playwright hosted UI token exchange asserts `redirect_uri=.../explorer/`; Cognito rejects unauthorized callback URIs by design
- Stub/live (P-15): fixture preview unchanged; live Cognito path needs this allowlist + web republish of `cognito.ts`
- Judge bar (`JUDGE.md`): never-kill intact; sign-in was blocked by allowlist mismatch, not by isolation rules

## What I shipped

- files: `infra/cognito.tf` callback/logout URLs; `web/src/lib/cognito.ts` stores authorize `redirect_uri` for token exchange; Playwright assertion
- outputs / env **names** (no secret values): uses existing `local.web_origin` / CloudFront domain; no new env vars
- tests: `web/tests/explorer.spec.ts` hosted UI callback case

## What I need

- from whom: Trevor (SSO + apply)
- contract / URL / header / path:
  - App authorize `redirect_uri`: `https://d13b678j60bhap.cloudfront.net/explorer/`
  - Cognito must allow: bare `https://d13b678j60bhap.cloudfront.net` **and** `.../explorer/`
  - Live Cognito was **not** updated in this session (`aws sts` → SSO token expired)

## Blocked on

`Trevor` SSO login + targeted Cognito client apply (or merge then apply). Web republish needed for the token-exchange fix to reach CloudFront.

## Contract reminder

Cognito app client callback/logout URL strings must exact-match the Hosted UI `redirect_uri` used by welcome sign-in and `/oauth2/token`.

## Live apply / SSO steps (Trevor)

SSO was expired locally (`Token has expired and refresh failed` for profile `ACIdeaScientistPermissionSet-093621304174`). Do **not** invent pool/client IDs — read them from Terraform outputs or the already-baked `NEXT_PUBLIC_COGNITO_*` values.

```bash
# 1) Refresh SSO
aws sso login --profile ACIdeaScientistPermissionSet-093621304174
export AWS_PROFILE=ACIdeaScientistPermissionSet-093621304174
export AWS_REGION=us-east-1

# 2) Confirm identity
aws sts get-caller-identity

# 3) Preferred: targeted Terraform apply after merge (or from this branch)
cd infra
terraform init
terraform plan  -target=aws_cognito_user_pool_client.web -var-file=envs/dev.tfvars
terraform apply -target=aws_cognito_user_pool_client.web -var-file=envs/dev.tfvars

# 4) Verify allowlist (read-only). Substitute pool/client from:
#    terraform output user_pool_id
#    terraform output user_pool_client_id
aws cognito-idp describe-user-pool-client \
  --user-pool-id "$USER_POOL_ID" \
  --client-id "$USER_POOL_CLIENT_ID" \
  --query 'UserPoolClient.{CallbackURLs:CallbackURLs,LogoutURLs:LogoutURLs}'

# Expect both:
#   https://d13b678j60bhap.cloudfront.net
#   https://d13b678j60bhap.cloudfront.net/explorer/

# 5) Republish web so CloudFront serves the token-exchange redirect_uri fix
#    (existing deploy/publish path — no new secrets)
```

Optional emergency CLI update is possible via `aws cognito-idp update-user-pool-client`, but it requires re-sending the full existing client settings; prefer Terraform `-target` so OAuth flows/scopes are not wiped.
