# Handoff — `trevor-docs-truth` — `docs/deploy-truth`

- Date: 2026-08-22
- Human: `Trevor`
- Agent id: `trevor-docs-truth`
- Branch: `trevor/docs/deploy-truth` (from main — #75 merged)
- PR: TBD
- Related: #48 (deploy), #54 (red team), #57 (submission checklist)

## Claimed paths (collision)

```
README.md
SECURITY.md
docs/ARCHITECTURE.md
handoffs/trevor-docs-deploy-truth.md
```

## Do not touch

```
vault/ (Alexis)   web/ (Michael)   contracts/ (locked)   infra/ (open on #74)
```

## Safe to run in parallel with

Anyone not editing the three docs above. #74 is open but touches only `infra/`.

## What I shipped

Documentation was wrong in **both** directions and this corrects it against AWS,
not against Terraform's output.

### Wrong in the pessimistic direction (understated)

`README.md` said *"As of this commit, nothing is deployed"* and **Public URL: TBD**.
The stack has been applied: 66 managed resources, both vault Lambdas, all five
routes. The P-15 table also said the read/audit API did not exist and that
`web/` did not exist; both landed (#68/#69/#71 and #75). Vault test count was
83, now 109. `SECURITY.md` said tenant isolation was "not yet implemented" and
the 403 attack "not demonstrable".

### Wrong in the optimistic direction (overstated — the dangerous half)

Two security claims were not merely unverified, they were **false**:

- **`SECURITY.md` traffic-interception row: "TLS 1.2_2021 minimum".** Not in
  force. `infra/cloudfront.tf` requests it, but the distribution uses
  `cloudfront_default_certificate = true`, which pins AWS to `TLSv1` and
  silently ignores the request. Confirmed with `get-distribution-config` on the
  live distribution. Raising it needs a custom domain + ACM cert. It is also the
  cause of a permanent Terraform diff.
- **`SECURITY.md` perimeter row: "WAF … associated with the HTTP API".**
  Impossible as built. WAFv2 attaches to API Gateway **REST** APIs, not **HTTP**
  APIs. The web ACL exists; `aws_wafv2_web_acl_association` (`api.tf:175`) fails
  on every apply, so it is associated with nothing and filters no traffic.

`docs/ARCHITECTURE.md` drew both claims in the diagram; both nodes corrected.
Mermaid still balances (6 `subgraph` / 6 `end`).

### What the docs now say is NOT live

Stated plainly, because this is the P-15 section a judge reads first:

1. The Explorer UI is **built, not published** — `web/` is on `main`, but the
   web bucket holds only `health.json`, so CloudFront returns 403 at `/`.
2. **No authenticated request has ever been made.** Every live check is
   unauthenticated (`/health` → 200; read and ingest → 401). No flight has been
   ingested, so nothing has been redacted in production and no cross-tenant read
   has been refused in production.
3. WAF filters nothing.

## Verification

- Every replacement asserted on an exact match before writing; 19 applied, 0 fuzzy.
- Residual scan for `nothing is deployed`, `not yet implemented`, `TLS 1.2_2021`,
  `83 passed`, `TBD`, `never been applied` → **clean**.
- Live values re-checked before writing: `/health` 200, `GET /v1/traces` 401,
  `POST /v1/traces` 401, both Lambdas present at 21655 bytes, five routes,
  `custom:tenant_id` set on both Cognito users, web bucket contains only
  `health.json`, CloudFront `/` 403.
- Test counts re-run, not copied: vault **109**, sdk **3**, demo-app **2**.

## What I need

- from whom: **Trevor** — merge. Nothing blocks on this.

## Blocked on

`nobody`.

## Note for the board

`api.tf:175` is still an always-failing resource. The docs now describe that
honestly, but the resource should either be removed (and the protection moved to
CloudFront, which WAF *can* attach to) or the API migrated to REST. Leaving it
means every future apply exits non-zero, which will eventually be mistaken for a
flaky deploy rather than a real one.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
