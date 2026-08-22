# Handoff — `alexis-inventory` — `vault-inventory`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-inventory`
- Branch: `alexis/docs/vault-inventory` (from main)
- Related: #55 (Alexis half), #50 (evidence packaged in a comment, no code)

## Claimed paths

```
README.md      (vault/redaction inventory rows + vault limitations/roadmap only)
handoffs/alexis-inventory.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
vault/ contracts/                                  (no code in this PR)
```

## What I shipped (#55 Alexis half)

`README.md` gained a **Technology inventory** section — it did not exist yet. My half is filled; Trevor's half is a clearly-marked italic line naming exactly what he owns (SDK/demo, Explorer, Terraform, AWS edge services, Actions/OIDC, pinned versions, SBOM/`trivy`) plus the assembly. I created the container rather than waiting so his rows drop straight in; if he prefers a different shape, the vault rows move wholesale.

Vault rows state the *why*, not just the *what* — two functions because that maps to the two trust levels; tenant as the DynamoDB partition key so isolation isn't a filter someone can forget; the deny-list authoritative because a judge-path guarantee cannot depend on a model being reachable.

**Vault limitations + roadmap** added under `## Limitations` — five, written as bounded scope with a next step, not apologies:
- deny-list is a known entity set (next: Presidio as a second pass, deny-list stays authoritative)
- reads paginate and cap at 50 (next: a cursor)
- no per-tenant rate limit, WAF inert (#100) (next: usage plans + ACL on CloudFront)
- flat 7-day retention (next: per-tenant TTL + an S3 lifecycle rule matching it)
- audit records reads, not exports (outside what an API can observe)

Also corrected one stale vault claim in the existing text: "83 tests" → 115, now with the live at-rest evidence pointer.

## Verification

Every claim checked against merged code before writing: `query_all` is imported in both `store_read.py` and `audit/log.py` (pagination is real, #106), `_MAX_LIMIT = 50` in `handlers/read.py`, `pytest vault` → **115 passed**. No claim that Presidio ships or that WAF protects ingest.

## Blocked on

`nobody`. Trevor merges and fills his half of the section.
