# TraceVault infra

Terraform for the 48h AWS SaaS path. Grafana is not the UI. Two Lambdas only. Ingest is **not** Cognito.

Do **not** `terraform apply` until a human says so. This PR only needs `terraform validate`.

## Layout

| File | What |
|---|---|
| `versions.tf` / `providers.tf` | Terraform >= 1.9, AWS provider ~> 5, default region `us-east-1` |
| `backend.tf.example` | S3 + DynamoDB lock — copy to `backend.tf` after bootstrap |
| `kms.tf` | CMK for payload S3 + DynamoDB |
| `storage.tf` | Payload bucket SSE-KMS, web origin (no website endpoint), Dynamo PK/SK + TTL |
| `api.tf` | HTTP API, CORS = CloudFront URL, JWT on GET, `X-Tenant-Key` ingest, `/health`, WAF, throttle |
| `lambda.tf` | `vault-ingest` + `vault-read` |
| `cognito.tf` | Pool, app client, hosted UI, `custom:tenant_id`, users `tenant-a` / `tenant-b`, no MFA |
| `cloudfront.tf` | OAC, HTTPS-only, SPA 403/404 → `/index.html`, CSP / HSTS / nosniff |
| `oidc.tf` | GitHub OIDC role **this repo + this stack only**. No `AKIA`. |
| `secrets.tf` | Placeholder secrets for tenant ingest keys (values not in git) |
| `cloudwatch.tf` | Lambda logs 7d. API 5xx ≥ 5 in 5 min. SNS only if `alarm_email` is set |
| `iam.tf` | No `s3:*` / `dynamodb:*` / `bedrock:*` on `*`; design evidence in [`../docs/IAM_DESIGN.md`](../docs/IAM_DESIGN.md) |

Capacity and abuse assumptions, including the 10× answer and limit behavior, are in [`../docs/SCALE.md`](../docs/SCALE.md). CI runs the IAM and capacity drift tests in `infra/tests/`.

## Remote state (issue #5 — do not close #5 here)

GitHub branch protection is a **repo setting**, not Terraform. Remote state is a **one-time human bootstrap** so credentials never land in git.

1. Create an S3 bucket in `us-east-1` with versioning + default encryption. Block public access.
2. Create a DynamoDB table `tracevault-tf-locks` with PK `LockID` (String).
3. Copy `backend.tf.example` → `backend.tf` and replace the bucket name.
4. `terraform init` (with backend).

Never commit access keys. GitHub Actions must assume `oidc_role_arn` via OIDC.

## Plan / apply (when a human asks)

```bash
export AWS_REGION=us-east-1
export TF_VAR_tenant_a_password='...'   # not in git
export TF_VAR_tenant_b_password='...'
cp backend.tf.example backend.tf        # after bootstrap
terraform init
terraform plan -var-file=envs/dev.tfvars.example
# terraform apply -var-file=envs/dev.tfvars.example   # human only
```

After apply, put ingest keys (Alexis maps `X-Tenant-Key` → tenant):

```bash
aws secretsmanager put-secret-value --secret-id "$TENANT_A_SECRET_ARN" \
  --secret-string '{"tenant_id":"tenant-a","key":"..."}'
aws secretsmanager put-secret-value --secret-id "$TENANT_B_SECRET_ARN" \
  --secret-string '{"tenant_id":"tenant-b","key":"..."}'
```

If `vault/` exists at the repo root, Lambda zips that tree (`vault.handlers.ingest.handler` / `vault.handlers.read.handler`). Otherwise the stub under `stubs/placeholder/` returns **501** so `validate` still runs. Trevor does not write `vault/` Python.

## Outputs → Michael `NEXT_PUBLIC_*`

| Output | Env |
|---|---|
| `api_url` | `NEXT_PUBLIC_API_URL` |
| `aws_region` (var) | `NEXT_PUBLIC_COGNITO_REGION` |
| `user_pool_id` | `NEXT_PUBLIC_COGNITO_USER_POOL_ID` |
| `user_pool_client_id` | `NEXT_PUBLIC_COGNITO_CLIENT_ID` |
| `cognito_domain` | `NEXT_PUBLIC_COGNITO_DOMAIN` (host, add `https://` if the SDK wants a URL) |

Also: `cloudfront_url` (UI + Cognito callback), `oidc_role_arn`, `table_name`, `payload_bucket`, `web_bucket`.

**`TRACEVAULT_INGEST_URL` ← `api_url`, not `ingest_url`.** Per `contracts/http.md` that variable is the API **base** URL: the SDK appends `/v1/traces` itself. The `ingest_url` output is the full endpoint (it already ends in `/v1/traces`) and exists for humans and `curl` — exporting it as `TRACEVAULT_INGEST_URL` makes the first live flight `POST .../v1/traces/v1/traces` and 404.

Send the **Cognito ID token** as `Authorization: Bearer …` on GET `/v1/traces*`. The JWT authorizer audience is the app client id (`custom:tenant_id` is on the ID token). Ingest uses `X-Tenant-Key` only.

## Contract this stack implements

- CORS origin = CloudFront URL, **not** `*`. Methods `GET,POST,OPTIONS`. Headers `Authorization,Content-Type,X-Tenant-Key`. Credentials off. OPTIONS is the HTTP API CORS preflight (204).
- `GET /health` — no Lambda. HTTP API v2 cannot MOCK; the route HTTP_PROXYs `{"ok":true}` from the web origin (`health.json`).
- `POST /v1/traces` → `vault-ingest`, no Cognito.
- `GET /v1/traces`, `GET /v1/traces/{trace_id}`, `GET /v1/traces/{trace_id}/audit` → `vault-read`, Cognito JWT.
- Dynamo TTL `expires_at` (Alexis writes epoch seconds). PITR **off**. Payload prefix `{tenant_id}/{trace_id}/`.
- No SSH `:22`, no EKS, no OpenSearch, no five Lambdas, no CloudTrail/GuardDuty/VPC-for-Lambda/Cognito MFA.

## Known gaps in the live stack (not aspirational — checked against AWS)

- **WAF is attached to CloudFront (fixed #100/#128), but evaluation is not yet confirmed.** WAFv2 cannot attach to an HTTP API, so the original `aws_wafv2_web_acl_association` failed on every apply; the fix replaced it with a `CLOUDFRONT`-scoped ACL set directly on the distribution's `web_acl_id`, and the attachment is confirmed live (`aws wafv2 list-web-acls --scope CLOUDFRONT`, distribution `WebACLId`). Not yet confirmed: minutes after apply, deliberate SQLi/XSS payloads at the edge still returned `200` and `AWS/WAFV2` metrics showed zero datapoints — plausibly still propagating (typically 10–20 min), but unverified until `BlockedRequests` shows a real hit. Flood protection until then is still API Gateway throttling plus the in-Lambda caps in `vault/`.
- **CloudFront's TLS floor is `TLSv1`, not `TLSv1.2_2021`.** `cloudfront.tf` requests `minimum_protocol_version = "TLSv1.2_2021"`, but the distribution uses `cloudfront_default_certificate = true`, which pins AWS's default cert and silently ignores that setting — confirmed against the live distribution config. Raising it needs a custom domain plus an ACM certificate.

Both are detailed with live evidence in [`../docs/RED_TEAM.md`](../docs/RED_TEAM.md) and [`../SECURITY.md`](../SECURITY.md).

## Import note

`aws_iam_openid_connect_provider.github` is account-global. If `token.actions.githubusercontent.com` already exists, `terraform import` it instead of creating a second provider.
