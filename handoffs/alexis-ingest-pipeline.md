# Handoff — `alexis-ingest` — `pipeline`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-ingest`
- Branch: `alexis/ingest/pipeline` (stacked on `alexis/redact/fail-closed`, PR #38 — merge #38 first; this PR auto-retargets to main when the base branch is deleted)
- PR: TBD
- Mission file: `skills/vault/agents/ingest.md` (scratchpad; issues #13 + #14, advances #17)

## Claimed paths (collision)

```
vault/errors.py
vault/ingest/
vault/store/
vault/handlers/
vault/tests/
handoffs/alexis-ingest-pipeline.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
contracts/                                         (hour 0 — PR #26, all three)
```

## Safe to run in parallel with

Anyone not writing `vault/`. NOT safe with another vault agent (shares `vault/tests/` conftest/fakes).

## What I shipped

- files: `vault/errors.py` (shared error envelope — issue #17: five contract codes + fixed messages; `forbidden` reads exactly "tenant mismatch" to match the locked fixture; adds `internal` 500 with a fixed PII-free body, not in the contract's 4xx table — flagging for review), `vault/ingest/{tenant_key,validate,pipeline}.py`, `vault/store/{keys,flight_store}.py`, `vault/handlers/ingest.py`, tests + boto3-shaped fakes under `vault/tests/`.
- auth: `X-Tenant-Key` (case-insensitive) checked against **both** per-tenant secrets from `TENANT_A_SECRET_ARN`/`TENANT_B_SECRET_ARN` (matches merged `infra/lambda.tf` + `infra/README.md` secret shape `{"tenant_id","key"}`), constant-time bytes compare, placeholder/unreadable secrets authenticate nobody. Unknown/missing → contract 401.
- validation: stdlib schema-lite per locked `span.schema.json` — required fields/types, enums, lengths, hash pattern, ≤100 spans, one `trace_id` per batch, **span.tenant_id must equal the key's tenant** (a tenant-a key cannot write spans labeled tenant-b), unknown span keys rejected (`additionalProperties:false` — unvalidated fields could smuggle PII past redaction). Violations → 400 `invalid`, messages name fields never values.
- redaction (authoritative, re-done at ingest): every free-text field masked via `vault.redact` — `name`, `error_message`, `prompt_preview`, all string values inside `attributes` and `events` recursively. Any unsafe → 400 `redaction_failed`, store never called. Incoming `prompt_hash`, `cost_usd`, token counts persisted unchanged.
- store: S3 `{tenant_id}/{trace_id}/{batch}.json` (complies with the IAM `PutObject` tenant-prefix policy; SSE-KMS headers when `KEY_ARN` set), then Dynamo summary item — **the Dynamo item is the commit point** (ingest role has no `s3:DeleteObject`; a failed Dynamo write leaves an unreachable orphan, never a half-visible flight). Item: PK `tenant_id`, SK `t#{trace_id}`, list-endpoint fields + `s3_keys`, `span_count`, `expires_at` (epoch, 7d default / `VAULT_TTL_DAYS`). Audit rows will use SK `a#{trace_id}#{ts}` (`vault/store/keys.py` — alexis-read/audit import these).
- env consumed (names only): `TABLE`, `BUCKET`, `KEY_ARN`, `TENANT_A_SECRET_ARN`, `TENANT_B_SECRET_ARN`, optional `VAULT_TTL_DAYS`. boto3 lazily imported (Lambda provides it; CI/tests never import it — all tests use injected fakes).
- tests: 64 passed (`python -m pytest vault`), `bandit -r vault -x "*/tests/*"` → 0. Covers: adversarial PII in attributes/events never at rest, redaction-fail → nothing stored, store-fail → 500 fixed body with no payload echo, handler never prints PII or the tenant key, 401/400 bodies byte-exact to contract, Decimal for Dynamo cost, base64 event bodies.

## What I need

- from whom: **Trevor** — merge order #38 → this. Same `vault.yml` bandit flag as the #38 handoff (`-x "*/tests/*"`). No new CI deps needed — still stdlib-only.
- from whom: **Trevor** — sanity-check two contract calls I made: (1) `internal` 500 code addition; (2) span.tenant_id-must-match-key rejection (vs silently rewriting). Both documented above; happy to change either.

## Blocked on

`nobody` for review; merge blocked on #38.

## Contract reminder

`POST /v1/traces` → `202 {"accepted":true,"trace_id":...}` | 401 `unauthorized` | 400 `invalid` | 400 `redaction_failed` (nothing stored) — bodies exactly `{"error":{"code","message"}}`. Read path may rely on: Dynamo SK prefixes `t#`/`a#` and item fields per `vault/store/keys.py`.

## Amendment (same day)

Issue #45 fixes landed on the base branch (deny-list lookarounds, key adjacency, redact input cap). Issue #46 hardening landed here: RecursionError from JSON nesting bombs -> 400 `invalid`; 1MB body cap -> 400 `invalid`; attributes deeper than 32 levels -> 400 `redaction_failed`; oversized single strings fail closed via the redact cap; injection strings stored inert. Adversarial suite: `vault/tests/ingest/test_adversarial.py`. 83 tests total.
