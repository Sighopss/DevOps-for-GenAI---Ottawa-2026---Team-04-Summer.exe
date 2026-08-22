# Handoff — `trevor-contracts` — `hour-0`

- Date: 2026-08-21
- Human: `Trevor`
- Agent id: `trevor-contracts`
- Branch: `trevor/contracts/hour-0`
- PR: `TBD`
- Mission file: Hour 0 Design gate — lock HTTP + auth, span schema, full-flight fixtures

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
contracts/
handoffs/trevor-contracts-hour-0.md
```

## Do not touch

```
sdk/
demo-app/
infra/
scripts/
.github/
Makefile
vault/
web/
PRODUCT.md
DESIGN.md
```

## Safe to run in parallel with

Nothing that writes `contracts/`. After this merges, lane agents (`trevor-sdk`, `trevor-demo`, `trevor-scripts`, `trevor-infra`, `trevor-ci`, Alexis vault, Michael web) can start **Build**. Do not start Build until this Design gate is merged.

## Handbook evidence (required — 2026 workbook)

Empty = incomplete PR. Copy from PLAN **Rubric 100** / P-ids.

- Lifecycle stage: `Design`
- P-ids this PR moves: `P-05`
- Rubric rows (pts): `Engineering 15` (one schema, two Lambdas, HTTP freeze), `Security 15` (403 not 404, fail-closed `redaction_failed`, ingest key ≠ JWT)
- Tests / attack shown: Fixtures only (no lane tests yet). Documented attack: tenant-b JWT + tenant-a `trace_id` → `403` `forbidden` / `tenant mismatch`. Fixtures contain **no** raw email/SSN (masked `[EMAIL]` / `[SSN]` + `prompt_hash`).
- Stub/live (P-15): **Stub.** Explorer Day 1 uses these full-flight fixtures. Live `GET /v1/traces*` is Day 2.

## What I shipped

- files:
  - `contracts/http.md` — HTTP + auth (ingest `X-Tenant-Key`, read JWT `custom:tenant_id`, `/health` mock, CORS CloudFront-only, error envelope, two Lambdas, `NEXT_PUBLIC_*`)
  - `contracts/span.schema.json` — TraceVaultSpan JSON Schema 2020-12
  - `contracts/fixtures/tenant-a-rag.json` — one `trace_id`, four spans (`http` root `demo.ask` → `rag` / `tool` / `llm`)
  - `contracts/fixtures/tenant-b-forbidden.json` — tenant-b full flight + 403 example against tenant-a `trace_id`
  - `handoffs/trevor-contracts-hour-0.md`
- outputs / env **names** (no secret values):
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_COGNITO_REGION`
  - `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
  - `NEXT_PUBLIC_COGNITO_CLIENT_ID`
  - `NEXT_PUBLIC_COGNITO_DOMAIN`
  - Ingest header: `X-Tenant-Key`
  - Read header: `Authorization: Bearer <Cognito access token>`
- tests: none on this PR (Design lock). Alexis maps 403/401/`redaction_failed` in vault tests after merge. Michael renders fixture A Day 1.

## What I need

- from whom: Alexis and Michael **must review** `contracts/` on this PR before merge.
- contract / URL / header / path:
  - Alexis: `POST /v1/traces` + `X-Tenant-Key`; `GET /v1/traces*` JWT `custom:tenant_id`; mismatch **403 not 404**; GET detail writes audit; error JSON exact.
  - Michael: list/detail/audit shapes; fixture A for Day 1; 403 chrome from `tenant-b-forbidden.json`; env names above — no hardcoded URLs.
  - Trevor lanes: emit schema-valid spans; Terraform CORS/JWT/`/health`/two Lambdas after this merges.

## Blocked on

`Alexis | Michael` (review `contracts/` on this thread). Human Trevor merges after that. Do not merge from this agent.

## Contract reminder

Ingest is **not** Cognito. Read JWT `custom:tenant_id` must match stored tenant → **403** not 404. `GET /health` is an API Gateway mock (no Lambda). CORS origin = CloudFront URL only. Two Lambdas only: `vault-ingest` → `vault.handlers.ingest.handler`, `vault-read` → `vault.handlers.read.handler`. Hour 0 fixtures are **full flights** (one `trace_id`, parent-child spans), not a single span.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and contracts/http.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
Alexis: vault/ against this HTTP + schema. Michael: web/ against fixtures then GET /v1/traces*.
```
