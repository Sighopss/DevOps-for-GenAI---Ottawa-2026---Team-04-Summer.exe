# Handoff — michael-m3 — flight-explorer-fixtures

- Date: 2026-08-22
- Human: Michael
- Agent id: `michael-m3`
- Branch: `michael/flight-explorer-fixtures`
- PR: `TBD`
- Mission / scope: Ship `web/` for the safe Michael slice: welcome `/`, Day 1 fixture-backed flight list + `?trace_id=` detail, and one-flight waterfall + RAG hops in Next.js 15 App Router with `output: 'export'`.

## Claimed paths (collision)

```
web/
handoffs/michael-m3-flight-explorer-fixtures.md
```

## Do not touch

```
vault/
sdk/
demo-app/
infra/
scripts/
.github/
Makefile
contracts/
README.md
AI_USAGE.md
```

## Safe to run in parallel with

Trevor infra, CI, docs, and governance work. Alexis ingest, redact, read, and audit work. Any PR that does not claim `web/`.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Build`
- P-ids this PR moves: `P-11`, `P-15`
- Rubric rows (pts): `Engineering 15`, `Security 15`, `Presentation 5`
- Tests / attack shown: `web/node_modules/.bin/eslint.cmd .`, `web/node_modules/.bin/next.cmd build`, `web/node_modules/.bin/playwright.cmd test` covering fixture render, masked PII, and tenant-b forbidden chrome
- Stub/live (P-15): Day 1 is fixture-only from `contracts/fixtures/tenant-a-rag.json` and `contracts/fixtures/tenant-b-forbidden.json`. Day 2 live `GET /v1/traces*` is still blocked on backend read + real 403 behavior and Trevor-provided `NEXT_PUBLIC_*` env outputs.
- Judge bar (`JUDGE.md`): never-kill intact on the web surface. UI shows masked placeholders and `REDACTED`, never raw SSN/email from fixtures, and shows contracted `403 forbidden` chrome instead of a blank missing page. Live tenant enforcement remains owned by Alexis/Trevor.

## What I shipped

- files: `web/` app shell, source, tests, config, and `pnpm-lock.yaml`
- outputs / env **names** (no secret values): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_DOMAIN`
- tests: welcome route builds, explorer fixture renders signed-in style list/detail, masked PII stays masked, tenant-b fixture produces contracted forbidden UI

## What I need

- from whom: `Alexis` and `Trevor`
- contract / URL / header / path: live `GET /v1/traces*` read path, real forbidden JSON for tenant mismatch, and deployed `NEXT_PUBLIC_*` values for the hosted UI + API base URL

## Blocked on

`Alexis | Trevor`

## Contract reminder

`web/` reads Day 1 fixtures only for this PR. Detail is via `?trace_id=` and not dynamic `[id]` routes. Day 2 live reads must stay on `GET /v1/traces*` with Cognito token handling and repo-owned env names only.