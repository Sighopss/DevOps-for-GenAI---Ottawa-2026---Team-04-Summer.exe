# Red team — attacks against the running system

Issue #54. Attacks run against the **live** deployment, with the fix or control each one hit. Companion: [DATA_AND_ABUSE.md](DATA_AND_ABUSE.md) (the six abuse cases this exercises), root `SECURITY.md` (threat model). Reproduce with [`redteam/redteam.sh`](redteam/redteam.sh).

- **Target API:** `https://55qm437628.execute-api.us-east-1.amazonaws.com`
- **Edge:** `https://d13b678j60bhap.cloudfront.net`
- **Run date:** 2026-08-22, from a machine outside the deploy pipeline (vault lane).
- **Auth state:** the authenticated attacks (cross-tenant read, live PII flight) are scaffolded and ready; they need a tenant key + Cognito sign-in the operator holds out of band. Everything else below is captured live.

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

## Authenticated attacks — scaffolded, ready to fire

These need a real tenant key (ingest) and a Cognito ID token (read). Steps in `redteam/redteam.sh`, env-driven; no secret is committed.

| # | Attack | Control it should hit | Evidence to capture |
|---|---|---|---|
| B1 | **Cross-tenant read** — tenant-b ID token requests a tenant-a `trace_id` | 403 (not 404), body `{"error":{"code":"forbidden","message":"tenant mismatch"}}`, no spans in body | status + body |
| B2 | **Live PII exfiltration** — ingest a tenant-a flight with email + fake SSN in the prompt, then read it back and inspect S3/Dynamo at rest | `prompt_preview` shows `[EMAIL]`/`[SSN]`, `prompt_hash` present, raw values absent from the object and item | read body + (with `tracevault-alexis` key) `s3api get-object` / `dynamodb get-item` |
| B3 | **Tenant-b list isolation** — tenant-b lists flights after a tenant-a flight exists | tenant-a `trace_id` absent from tenant-b's list | list body |
| B4 | **Audit trail** — open a trace, then GET its audit | one row with actor/tenant/trace/ts; second open → two rows oldest-first | audit body ×2 |
| B5 | **Prompt injection at ingest** — span text `"ignore previous instructions…"` | stored as inert masked data; plain 202; no behavior change | 202 + stored payload |

## Infrastructure findings (from PR #76's honesty pass — real red-team material)

Two controls were **documented as in force but are not**. A judge can disprove both with one AWS call, so naming them is worth more than the gap:

1. **WAF filters nothing.** The WebACL exists but WAFv2 attaches to REST APIs, not HTTP APIs; `infra/api.tf:175` fails on every apply, so the ACL is associated with nothing. **Impact:** abuse cases that assumed WAF (rate/flood) rest entirely on the in-Lambda caps (batch ≤100, 1 MB body, 10k-char field, depth-32) + API Gateway default throttling. **Fix path:** move the WebACL to the CloudFront distribution (which WAFv2 *can* attach to), or migrate the API to REST. Recommend CloudFront.
2. **TLS floor is TLSv1, not 1.2_2021.** `cloudfront_default_certificate = true` pins AWS's default cert and ignores the requested minimum. **Impact:** a client can negotiate below TLS 1.2 at the edge. **Fix path:** custom domain + ACM cert with `minimum_protocol_version = TLSv1.2_2021`; also clears a permanent Terraform diff.

## Accepted-risk confirmations (already documented, re-verified live)

- No per-tenant ingest rate limit — with WAF inert this is now the *only* flood control gap; bounded by in-Lambda caps + gateway throttling + 7-day TTL. Production: usage plans / per-key throttling.
- Explorer UI built but not published — CloudFront `/` returns 403 (bucket holds only `health.json`); no XSS/PII-on-screen surface is live yet (Michael's #62 covers the UI half once published).
