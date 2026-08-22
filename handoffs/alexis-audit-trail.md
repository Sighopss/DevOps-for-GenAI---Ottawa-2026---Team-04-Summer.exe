# Handoff — `alexis-audit` — `trail`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-audit`
- Branch: `alexis/audit/trail` (from main — #38/#44 merged)
- PR: TBD
- Mission file: `skills/vault/agents/audit.md` (scratchpad; issue #16, first half)

## Claimed paths (collision)

```
vault/audit/
vault/tests/audit/
vault/tests/fakes.py        (added FakeTable.query — shared test infra)
handoffs/alexis-audit-trail.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
contracts/                                         (locked)
```

## Safe to run in parallel with

Anyone not writing `vault/` (currently open: #67 trevor/ci/sha-pin — no overlap).

## What I shipped

- files: `vault/audit/{__init__,models,log}.py`, `vault/tests/audit/{test_record,test_list_events}.py`, `FakeTable.query` in `vault/tests/fakes.py`.
- `record(actor, tenant_id, trace_id)` writes one row to the traces table: SK `a#{trace_id}#{ts}#{entropy}` (entropy suffix so same-microsecond events never overwrite), attrs exactly `actor / tenant_id / trace_id / ts / expires_at` — an audit row physically cannot leak prompt data because it never holds any. Same TTL policy as span data (`VAULT_TTL_DAYS`, default 7).
- `list_events(tenant_id, trace_id)` → oldest-first `AuditEvent`s, queried with a string KeyConditionExpression (no boto3 import anywhere; Lambda wiring lazy-imports, tests inject fakes). Tenant partitioning + the `a#` prefix keep other tenants' events, other traces' events, and flight summary rows out — tested, including the same-trace_id-different-tenant case.
- This package does **not** parse JWTs — the read handler (next mission) extracts the actor claim and calls `record` + `list_events` on `GET /v1/traces/{trace_id}/audit`.
- tests: 93 total green (`python -m pytest vault`), `bandit -r vault -x "*/tests/*"` → 0.

## What I need

- from whom: nobody. Read mission (`alexis-read`) completes issue #16's route half.

## Blocked on

`nobody`.

## Contract reminder

`GET /v1/traces/{trace_id}/audit` → `200 {"events":[{"actor","tenant_id","trace_id","ts"}]}` and the GET itself **writes** a row (read mission wires that). `AuditEvent.to_dict()` is that exact shape.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
