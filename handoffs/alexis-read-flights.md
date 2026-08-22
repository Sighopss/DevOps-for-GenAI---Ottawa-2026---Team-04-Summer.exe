# Handoff — `alexis-read` — `flights`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-read`
- Branch: `alexis/read/flights` (stacked on `alexis/audit/trail`, PR #68 — merge #68 first; this auto-retargets when the base branch is deleted)
- PR: TBD
- Mission file: `skills/vault/agents/read.md` (scratchpad; issue #15 + route half of #16)

## Claimed paths (collision)

```
vault/read/
vault/handlers/read.py
vault/tests/read/
vault/tests/fakes.py        (FakeS3Client.get_object)
handoffs/alexis-read-flights.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
contracts/                                         (locked)
```

## Safe to run in parallel with

Anyone not writing `vault/` (open: #67 sha-pin — no overlap).

## What I shipped

- files: `vault/read/{__init__,tenant_guard,store_read}.py`, `vault/handlers/read.py`, `vault/tests/read/{conftest,test_read_routes,test_isolation}.py`, `FakeS3Client.get_object`.
- `GET /v1/traces?limit=50` — Query on the caller's `custom:tenant_id` partition, `t#` prefix only (audit rows invisible), newest-first by `start_time`, limit clamped to 50 (>50 clamps; non-numeric/≤0 → 400 `invalid`). `flights[]` rows are exactly the contract's seven fields; Decimal→float for JSON.
- `GET /v1/traces/{trace_id}` — `{"trace_id","tenant_id","expires_at","spans":[...]}`, spans loaded from the item's `s3_keys`. **403 vs 404:** miss under the caller's tenant, then check the other tenant's partition — found there → 403 with the byte-exact fixture body (`"tenant mismatch"`), found nowhere → 404. Tested against fixtures-shaped flights ingested through the real pipeline.
- `GET /v1/traces/{trace_id}/audit` — same guard, then `vault.audit.record(actor,…)` **then** `list_events` (viewing the trail is itself audited; the fresh row is in the response). Actor = `cognito:username`/`username`/`sub` claim. Forbidden attempts do not write into the victim tenant's trail.
- Auth: gateway-verified JWT claims only (no re-verification). Missing `custom:tenant_id` — e.g. a Cognito *access* token, which passes the authorizer — → 401 fail-closed per `contracts/http.md`. Unexpected exceptions → fixed `internal` 500, no claim/payload echo.
- Handler tolerates stage-prefixed `rawPath` and prefers `pathParameters` (route keys confirmed against `infra/api.tf`).
- tests: 108 total green (`python -m pytest vault`), bandit 0. Seeded through the real ingest pipeline so list/detail shapes are proven end-to-end: ingest → store → read.

## What I need

- from whom: **Trevor** — merge #68 then this. After both: all four Alexis core issues (#12–#16) have their code on main; live-AWS checks (#18 D2 half, #53, #54) need applied Terraform + deployed Lambdas.
- from whom: **Michael** — list/detail/audit JSON shapes are final per above; fixture files remain the Day-1 source.

## Blocked on

`nobody` for review; merge blocked on #68.

## Contract reminder

`GET /v1/traces*` responses and error bodies are byte-exact to `contracts/http.md` + the 403 fixture. Cross-tenant = 403, unknown = 404, claim-less = 401 — never collapse those.