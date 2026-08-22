# Handoff — `trevor-fix-edge` — `fix/edge-and-observability`

- Date: 2026-08-22
- Human: `Trevor`
- Branch: `trevor/fix/edge-and-observability` (from main — #130 merged)
- Closes: #131, #132, #126, #121. Advances: #123, #136.

## Claimed paths

```
infra/cloudfront.tf  infra/api.tf  infra/cloudwatch.tf  infra/storage.tf
infra/lambda.tf  infra/variables.tf  infra/envs/*.tfvars.example
handoffs/trevor-fix-edge-observability.md
```

## Do not touch

```
web/ (Michael)   vault/ (Alexis)   .github/ (PR #133)   README + docs (PR #135)
```

## What I shipped

### #131 — the Explorer was unreachable by clicking

`web/src/app/page.tsx` renders `<Link href="/explorer">`. The Next export is
**flat** (`next.config.ts` sets `output: "export"` with no `trailingSlash`), so the
page is stored under the key `explorer.html`. S3 serves keys literally, so
`/explorer` missed, fell through `custom_error_response`, and returned **the
welcome page at HTTP 200**.

Measured live before the fix:

| Path | HTTP | Bytes | Actually served |
|---|---|---|---|
| `/` | 200 | 5799 | welcome |
| `/explorer/` | 200 | **5799** | **welcome again** — this is the linked path |
| `/explorer.html` | 200 | 16224 | the real Explorer |

A judge clicking sign-in landed back on the welcome page. **A clean rebuild alone
would not have fixed this** — clean URLs cannot resolve against flat S3 keys
without a rewrite.

Added `aws_cloudfront_function.uri_rewrite` on viewer-request:

- `/` → `/index.html`
- `/explorer` → `/explorer.html`
- `/explorer/` → `/explorer.html` — deliberately tolerant, because the currently
  deployed bundle links **with** the trailing slash while `main` builds **without**
  it. This makes the fix work against either bundle.
- anything already carrying an extension is untouched, which is what keeps
  `/health.json` — a never-kill — working

ES5 only: the CloudFront Functions runtime has no `String.includes` or
`endsWith`. The logic was tested against ten URI shapes, 0 failures, including
`/health.json`, `/_next/…​.js`, `/_next/…​.css`, `/404.html` and `/explorer.txt`.

### #132 — 403 and 404 both mapped to 200

Both `custom_error_response` blocks rewrote to `/index.html` with
**`response_code = 200`**, so every missing object answered 200. That is what hid
#131 for a full day: no status-code check could fail. It would also have let a
missing `health.json` report healthy while serving HTML, and `GET /health`
proxies to that object.

Now 403 → `/404.html` at **404**, and 404 → `/404.html` at **404**. The 403
mapping is kept because S3 + OAC returns 403, not 404, for a missing key when the
bucket policy grants `GetObject` without `ListBucket`.

### #126 — no API access logging

`AccessLogSettings` was null. A refused cross-tenant read (403), a throttled
request (429), and anything the JWT authorizer rejected *before* reaching a
Lambda were all invisible — the authorizer path never touches our code, so the
Lambda logs could not have shown it.

Added `aws_cloudwatch_log_group.api_access` (7-day retention, matching the Lambda
groups so the whole request path expires together) and a JSON access-log format.

Deliberately **absent** from the format: `Authorization`, `X-Tenant-Key`, and any
request body. `custom:tenant_id` **is** recorded — it is a tenant id, not a
credential, and it is what lets an access line answer "who".

`detailed_metrics_enabled = true` so per-route metrics exist for alarms.

### #121 — S3 lifecycle matching the DynamoDB TTL

A payload object outliving its Dynamo row is data we promised to delete and did
not. Added a lifecycle rule on the payload bucket. It and the Lambdas'
`VAULT_TTL_DAYS` now both read one new `var.retention_days` (default 7), so the
two cannot drift — which was the actual point of the issue. Also aborts
incomplete multipart uploads after 1 day; otherwise they bill indefinitely and
are invisible.

### #123 — partial, and honest about it

`alarm_email` lives in the gitignored `dev.tfvars`, so only the examples could be
fixed here. Both now carry a comment explaining that an empty value means
`aws_sns_topic.alarms` is never created (`count = 0`) and the alarm gets
`alarm_actions = []`. **Trevor still has to set the real value and confirm the
subscription email** — an unconfirmed subscription notifies nobody, so applying
alone is not enough.

## Verification

- `terraform fmt -check` → clean.
- `terraform validate` → **Success! The configuration is valid.**
- Rewrite logic tested against 10 URI shapes → 0 failures.
- `terraform plan` was **not** run and nothing was applied. Plan and apply against
  real state are Trevor's; I do not have that permission.

## Blocked on

**Trevor.** After merge:

1. `terraform apply`. Expect a CloudFront distribution update — roughly 30 seconds
   to propagate, so do not judge it instantly.
2. Rebuild and re-sync the web bundle so it and the bucket agree. The bucket
   currently holds **two build shapes**: `404/index.html` (15:13, directory-style)
   and `explorer.html` (14:39, flat). Do not `--delete` without confirming
   `health.json` survives — it is a never-kill.
3. Verify by **bytes, not status code** — 200 is exactly what was lying before:
   `curl -s $CF/explorer | wc -c` should be ~16224, not ~5799.
4. Set `alarm_email`, apply, and confirm the subscription email (#123).
5. #136 stays open. The WAF is attached to CloudFront but still could not be shown
   to evaluate traffic; nothing in this PR changes that.

## Pickup prompt

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
