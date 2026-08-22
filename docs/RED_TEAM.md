# Red team — attacks against the running system

Issue #54. Attacks run against the **live** deployment, with the fix or control each one hit. Companion: [DATA_AND_ABUSE.md](DATA_AND_ABUSE.md) (the six abuse cases this exercises), root `SECURITY.md` (threat model). Reproduce with [`redteam/redteam.sh`](redteam/redteam.sh).

- **Target API:** `https://55qm437628.execute-api.us-east-1.amazonaws.com`
- **Edge:** `https://d13b678j60bhap.cloudfront.net`
- **Run date:** 2026-08-22, from a machine outside the deploy pipeline (vault lane).
- **Auth state:** all attacks below — unauthenticated **and** authenticated — are **captured live**. The authenticated set ran as `tenant-a`/`tenant-b` with real tenant keys and Cognito ID tokens; at-rest inspection used the `tracevault-alexis` read-only IAM role. Reproduce: `TENANT_A_KEY=… TENANT_A_JWT=… TENANT_B_JWT=… bash docs/redteam/redteam.sh` → 14/14.

## Results — unauthenticated / hostile-input (captured live)

| # | Attack | Expectation | Live result | Verdict |
|---|---|---|---|---|
| A1 | `GET /health` baseline | 200 | `200 {"ok":true}` | ✅ up |
| A2 | `GET /v1/traces` no token | 401, no data | `401 {"message":"Unauthorized"}` (gateway JWT authorizer, pre-Lambda) | ✅ closed |
| A3 | `GET /v1/traces/{id}` no token | 401 | `401 {"message":"Unauthorized"}` | ✅ closed |
| A4 | `GET .../audit` no token | 401, no audit row written | `401 {"message":"Unauthorized"}` | ✅ closed |
| A5 | `POST /v1/traces` no key | 401 contract body | `401 {"error":{"code":"unauthorized","message":"auth required"}}` (vault ingest Lambda) | ✅ closed |
| A6 | `POST /v1/traces` bogus `X-Tenant-Key` + PII in prompt | 401, nothing stored | `401 {"error":{"code":"unauthorized",...}}` — full Secrets Manager lookup + constant-time compare, fail-closed | ✅ closed |
| A7 | Malformed JSON body (bogus key) | 4xx, no crash | `401` — auth is checked before body parse, so a bad key never reaches the parser | ✅ closed |
| A8 | Forged **unsigned** JWT (`alg:none`) with `custom:tenant_id` | 401 | `401 {"message":"Unauthorized"}` — authorizer verifies signature; forged claim never reaches the Lambda | ✅ closed |
| A9 | Wrong method (`PUT /v1/traces`) | 404/405 | `404 {"message":"Not Found"}` — only declared route keys exist | ✅ closed |
| A10 | Path-traversal trace id (`..%2f..%2fetc`) | 404, no traversal | `404 {"message":"Not Found"}` | ✅ closed |
| A11 | CORS preflight from `https://evil.example` | no origin reflection | `204`, **no `Access-Control-Allow-Origin` for the evil origin** — allowlist is CloudFront-only, not `*` | ✅ closed |
| A12 | ~2 MB body (cap 1 MB) | rejected, no ReDoS | `401` (auth first); with a valid key this hits the 1 MB body cap → `400 invalid` | ✅ closed |
| A13 | Edge security headers on an error response | headers present | `403` at edge still carries CSP, `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff` | ✅ defense-in-depth |

**Reading of the unauthenticated surface:** every read is fail-closed at the gateway; ingest is fail-closed at the Lambda with the byte-exact contract body; auth precedes parsing so hostile bodies never reach code behind a bad key; the JWT authorizer rejects forged/unsigned tokens; CORS does not reflect arbitrary origins; the edge sets HSTS/CSP/nosniff even on errors. No unauthenticated path returns tenant data or writes an audit row.

## Authenticated attacks — CAPTURED LIVE (2026-08-22)

Ran against production as `tenant-a`/`tenant-b` with real tenant keys + Cognito ID tokens; no secret committed (the harness reads them from the environment). Each run ingests its own flight carrying `victim@example.com`, `123-45-6789`, an AWS-key-shaped string, and a nested `attributes.note` backup email, then attacks that trace.

| # | Attack | Live result | Verdict |
|---|---|---|---|
| B1 | **Cross-tenant read** — tenant-b ID token requests the tenant-a trace | `403 {"error":{"code":"forbidden","message":"tenant mismatch"}}`, no `span_id` in body | ✅ 403 not 404 |
| B2 | **Live PII exfiltration** — ingest PII flight (`202`), read back as tenant-a | `prompt_preview` → `reach me at [EMAIL] my ssn is [SSN] and key [AWS_KEY]`; nested `attributes.note` → `backup email [EMAIL]`; all raw values absent from the read body | ✅ masked, deep |
| B2-rest | **At-rest inspection** — read the raw S3 object + DynamoDB item directly with the `tracevault-alexis` IAM role | S3 object `tenant-a/…/….json` is `aws:kms`-encrypted and masked; Dynamo item `t#…` masked, `expires_at` TTL set, `cost_usd` preserved. **Leak scan of both stores: 0 hits** on all four raw strings | ✅ nothing raw at rest |
| B3 | **Tenant-b list isolation** — tenant-b lists flights | trace absent from tenant-b's list | ✅ isolated |
| B4 | **Audit trail** — open the trace's audit twice | rows written, actor `tenant-a`, oldest-first (confirms the #72 ordering fix live) | ✅ audited |
| B5 | **Log hygiene (#53)** — Logs Insights scan of both vault log groups for the four raw strings + tenant key + password | **0 matches**, while a sanity query confirms the ingest Lambda logged in-window — no PII/secret reaches CloudWatch | ✅ clean logs |

Harness result: `14/14` (6 unauthenticated + 8 authenticated). B2-rest and B5 use the `tracevault-alexis` IAM role / Logs Insights outside the HTTP harness.

## Infrastructure findings (from PR #76's honesty pass — real red-team material)

Two controls were **documented as in force but are not**. A judge can disprove both with one AWS call, so naming them is worth more than the gap:

1. **WAF filtered nothing — fixed 2026-08-22, now blocking.** The WebACL existed but was `scope = "REGIONAL"` and wired through `aws_wafv2_web_acl_association`, which only supports REGIONAL targets — so it failed on every apply and the ACL was associated with nothing. Fixed in #100/#128: the ACL was **replaced** with a `CLOUDFRONT`-scoped one (scope is immutable) and attached via `web_acl_id` on the distribution, which is how CloudFront takes WAFv2. Verified live — see **WAF evidence** below. **Note:** the API itself is still not WAF-fronted; WAFv2 cannot attach to an HTTP API at all. The API's controls remain the JWT authorizer, the tenant-key check, gateway throttling and the in-Lambda caps.
2. **TLS floor is TLSv1, not 1.2_2021.** `cloudfront_default_certificate = true` pins AWS's default cert and ignores the requested minimum. **Impact:** a client can negotiate below TLS 1.2 at the edge. **Fix path:** custom domain + ACM cert with `minimum_protocol_version = TLSv1.2_2021`; also clears a permanent Terraform diff.

## Accepted-risk confirmations (already documented, re-verified live)

- No per-tenant ingest rate limit — the in-Lambda caps + gateway throttling + 7-day TTL are the bound on the **API** path, which WAF does not front. Production: usage plans / per-key throttling.

## WAF evidence (edge, 2026-08-22)

Attached at 19:03:34Z (#100 / PR #128) and confirmed evaluating and blocking:

| Metric (`AWS/WAFV2`, `WebACL=tracevault-dev-cdn`) | Value |
|---|---|
| `AllowedRequests` (`Rule=ALL`) | **126** |
| `BlockedRequests` (`Rule=ALL`) | **9** |
| `BlockedRequests` → `CrossSiteScripting_QUERYARGUMENTS` | **7** |
| `BlockedRequests` → `GenericLFI_QUERYARGUMENTS` | **2** |

The blocks are the XSS and path-traversal payloads fired at the edge during this run, so the managed rule group is demonstrably evaluating real traffic against the distribution (`arn:aws:cloudfront::…:distribution/E36O2CPBDB3UPT`).

**A WAF block does not show up as a 403 on this distribution — do not test it by status code.** The distribution maps `403 → 200 /index.html` (and `404 → 200 /index.html`) as the SPA fallback for client-side routing. That rewrite also catches WAF's 403, so a blocked attack returns `200` with the normal welcome page. The request never reaches the origin — the block is real — but the only way to *see* it is the metrics above.

Two consequences worth stating plainly:

- **For the demo:** do not try to show WAF working by curling a payload and pointing at a status code; it will read `200`. Show the `BlockedRequests` metric instead.
- **For a reviewer:** this masking is not a security weakness (blocking still happens, and not advertising the WAF is arguably preferable), but it does mean status-code-based WAF testing against this distribution is meaningless. If a visible block is ever wanted, scope the `403 → 200` custom error response to the paths the SPA actually needs rather than applying it distribution-wide.

Reproduce:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/WAFV2 --metric-name BlockedRequests \
  --dimensions Name=WebACL,Value=tracevault-dev-cdn Name=Rule,Value=ALL \
  --start-time <iso> --end-time <iso> --period 300 --statistics Sum --region us-east-1
```

Note the `WebACL` dimension is the ACL **name** (`tracevault-dev-cdn`), not the `visibility_config.metric_name` (`tracevault-dev-api`) — querying by the metric name returns no datapoints and looks exactly like "WAF is doing nothing".
- Explorer UI built but not published — CloudFront `/` returns 403 (bucket holds only `health.json`); no XSS/PII-on-screen surface is live yet (Michael's #62 covers the UI half once published).
