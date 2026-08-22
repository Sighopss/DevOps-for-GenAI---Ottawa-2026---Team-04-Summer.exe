# HTTP + auth

Hour 0 lock. Do not invent a second API.

### Auth

| Surface | Auth | Who |
|---|---|---|
| `POST /v1/traces` | `X-Tenant-Key` only. Key → `tenant-a` or `tenant-b` via Secrets Manager. | Trevor provisions. Alexis validates and maps key → `tenant_id`. |
| `GET /v1/traces*` | `Authorization: Bearer <Cognito access token>` | Trevor: pool, app client, hosted UI domain, callback = CloudFront URL, `custom:tenant_id`. Alexis: JWT `custom:tenant_id` must match stored tenant. Mismatch → **403** (not 404). |
| `GET /health` | none | Trevor: API Gateway mock. No Lambda. |

Ingest is **not** Cognito. Users `tenant-a` and `tenant-b` have `custom:tenant_id` = username. Passwords via `TF_VAR_*`, not git. No force-change-on-first-login (judges sign in once).

### Error JSON

```json
{ "error": { "code": "unauthorized", "message": "auth required" } }
```

`code`: `unauthorized` (401), `forbidden` (403), `not_found` (404), `invalid` (400), `redaction_failed` (400, fail-closed, nothing stored). `message` never contains PII, prompts, or keys.

### Routes

| Method | Path | Auth | Code | AWS | Success |
|---|---|---|---|---|---|
| `GET` | `/health` | none | — | Trevor mock | `200 {"ok":true}` |
| `POST` | `/v1/traces` | tenant key | Alexis ingest→redact→store | `vault-ingest` | `202 {"accepted":true,"trace_id":"<id>"}` |
| `GET` | `/v1/traces?limit=50` | JWT | Alexis read | `vault-read` | `200 {"flights":[...]}` |
| `GET` | `/v1/traces/{trace_id}` | JWT | Alexis read | `vault-read` | `200 {"trace_id","tenant_id","expires_at","spans":[...]}` |
| `GET` | `/v1/traces/{trace_id}/audit` | JWT | Alexis audit | `vault-read` | `200 {"events":[{"actor","tenant_id","trace_id","ts"}]}` |
| `OPTIONS` | those paths | CORS | — | Trevor | 204 |

List `flights[]`: `trace_id`, `tenant_id`, `start_time`, `end_time`, `cost_usd`, `status`, `prompt_preview`. Tenant-scoped from JWT. `limit` max 50. Get spans = span schema. Audit GET also **writes** a row.

`POST /v1/traces` body is `{ "spans": [ TraceVaultSpan, ... ] }`.

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
