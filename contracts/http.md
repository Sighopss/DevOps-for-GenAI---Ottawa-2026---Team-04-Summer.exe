# HTTP + auth

Hour 0 lock. Do not invent a second API.

### Auth

| Surface | Auth | Who |
|---|---|---|
| `POST /v1/traces` | `X-Tenant-Key` only. Key → `tenant-a` or `tenant-b` via Secrets Manager. | Trevor provisions. Alexis validates and maps key → `tenant_id`. |
| `GET /v1/traces*` | `Authorization: Bearer <Cognito **ID** token>` | Trevor: pool, app client, hosted UI domain, callback = CloudFront URL, `custom:tenant_id`. Alexis: JWT `custom:tenant_id` must match stored tenant. Mismatch → **403** (not 404). |
| `GET /health` | none | Trevor: **no Lambda**. HTTP API (API Gateway v2) has no `MOCK` integration type, so `/health` is an `HTTP_PROXY` route to a static `health.json` on the CloudFront origin. Body stays `{"ok":true}`. |

**ID token, not access token.** Cognito puts custom attributes on the **ID** token only — a Cognito *access* token carries `sub`, `client_id`, `scope`, and `username`, but never `custom:tenant_id`. The HTTP API JWT authorizer accepts either token, so sending the wrong one does **not** fail at the gateway: it reaches `vault-read` with no tenant claim. Fail closed there (`401 unauthorized`), never open.

Ingest is **not** Cognito. Users `tenant-a` and `tenant-b` have `custom:tenant_id` = username. Passwords via `TF_VAR_*`, not git. No force-change-on-first-login (judges sign in once).

### Error JSON

```json
{ "error": { "code": "unauthorized", "message": "auth required" } }
```

`code`: `unauthorized` (401), `forbidden` (403), `not_found` (404), `invalid` (400), `redaction_failed` (400, fail-closed, nothing stored). `message` never contains PII, prompts, or keys.

### Routes

| Method | Path | Auth | Code | AWS | Success |
|---|---|---|---|---|---|
| `GET` | `/health` | none | — | Trevor `HTTP_PROXY` → `health.json` (no Lambda) | `200 {"ok":true}` |
| `POST` | `/v1/traces` | tenant key | Alexis ingest→redact→store | `vault-ingest` | `202 {"accepted":true,"trace_id":"<id>"}` |
| `GET` | `/v1/traces?limit=50` | JWT | Alexis read | `vault-read` | `200 {"flights":[...]}` |
| `GET` | `/v1/traces/{trace_id}` | JWT | Alexis read | `vault-read` | `200 {"trace_id","tenant_id","expires_at","spans":[...]}` |
| `GET` | `/v1/traces/{trace_id}/audit` | JWT | Alexis audit | `vault-read` | `200 {"events":[{"actor","tenant_id","trace_id","ts"}]}` |
| `OPTIONS` | those paths | CORS | — | Trevor | 204 |

List `flights[]`: `trace_id`, `tenant_id`, `start_time`, `end_time`, `cost_usd`, `status`, `prompt_preview`. Tenant-scoped from JWT. `limit` max 50. Get spans = span schema. Audit GET also **writes** a row.

`POST /v1/traces` body is `{ "spans": [ TraceVaultSpan, ... ] }`.

### Fixtures (locked names)

Day 1 Explorer reads these; do not rename them.

| File | What |
|---|---|
| `contracts/fixtures/tenant-a-rag.json` | tenant-a full flight — one `trace_id`, four spans (`http` root `demo.ask` → `rag` / `tool` / `llm`) |
| `contracts/fixtures/tenant-b-forbidden.json` | tenant-b full flight **plus** the 403 example against a tenant-a `trace_id` |

Both carry masked `prompt_preview` (`[EMAIL]` / `[SSN]`) + `prompt_hash`. No raw PII.

### CORS (Trevor)

Allow origin = CloudFront URL only (not `*`). Methods `GET,POST,OPTIONS`. Headers `Authorization,Content-Type,X-Tenant-Key`. Credentials off.

### Two Lambdas, five packages

Alexis writes `vault/{ingest,redact,store,read,audit}/`. Trevor does **not** create five functions.

- `vault-ingest` → `vault.handlers.ingest.handler`
- `vault-read` → `vault.handlers.read.handler`

Trevor zips `vault/`. Alexis owns the handler files.

### Web env (Michael)

```
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_COGNITO_REGION
NEXT_PUBLIC_COGNITO_USER_POOL_ID
NEXT_PUBLIC_COGNITO_CLIENT_ID
NEXT_PUBLIC_COGNITO_DOMAIN
```

Tokens in memory or sessionStorage. Trevor outputs these values. Michael does not hardcode URLs.

### Env var semantics (SDK / demo)

`TRACEVAULT_INGEST_URL` is the **API base URL**, with no path. The SDK appends `/v1/traces` itself. Terraform's `ingest_url` output is the full endpoint (it already ends in `/v1/traces`) and must **not** be fed into this variable — use the `api_url` output. Feeding `ingest_url` in produces `POST .../v1/traces/v1/traces` and a 404 on the live demo flight.

| Env var | Value | Terraform output |
|---|---|---|
| `TRACEVAULT_INGEST_URL` | API base, no path | `api_url` |
| `NEXT_PUBLIC_API_URL` | API base, no path | `api_url` |
