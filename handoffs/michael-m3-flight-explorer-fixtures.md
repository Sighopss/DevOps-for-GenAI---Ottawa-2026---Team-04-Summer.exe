# Handoff — michael-m3 — flight-explorer-fixtures

- Date: 2026-08-22
- Human: Michael
- Agent id: `michael-m3`
- Branch: `michael/flight-explorer-fixtures`
- PR: `75`
- Mission / scope: Finish Michael's remaining explorer slice across `PRODUCT.md`, `DESIGN.md`, and `web/`: welcome `/`, fixture and live list/detail via `?trace_id=`, waterfall + RAG hops, audit / tenant strip, contracted 403 chrome, and Playwright coverage in Next.js 15 App Router with `output: 'export'`.

## Claimed paths (collision)

```
PRODUCT.md
DESIGN.md
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
- Tests / attack shown: `web/node_modules/.bin/eslint.cmd src tests playwright.config.ts next.config.ts eslint.config.mjs`, `web/node_modules/.bin/next.cmd build`, `web/node_modules/.bin/playwright.cmd test --workers 1` covering fixture render, masked PII, and live tenant-b forbidden chrome
- Stub/live (P-15): Day 1 is still fixture-only from `contracts/fixtures/tenant-a-rag.json` and `contracts/fixtures/tenant-b-forbidden.json`. Day 2 live `GET /v1/traces*` and `GET /v1/traces/{trace_id}/audit` are now wired in `web/`; final end-to-end proof still depends on deployed `NEXT_PUBLIC_*` values and a live URL.
- Judge bar (`JUDGE.md`): never-kill intact on the web surface. UI shows masked placeholders and `REDACTED`, never raw SSN/email from fixtures, keeps tokens in sessionStorage, and renders `403 forbidden` chrome instead of a blank missing page. Live tenant enforcement is now exercised through the real read contract.

## What I shipped

- files: `PRODUCT.md`, `DESIGN.md`, `web/` app shell, source, tests, config, and `pnpm-lock.yaml`
- outputs / env **names** (no secret values): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_DOMAIN`
- tests: welcome route builds, explorer fixture renders signed-in style list/detail, tenant switcher reaches tenant-b fixture data, masked PII stays masked, live tenant-b produces real forbidden UI from mocked `GET /v1/traces*`

## What I need

- from whom: `Trevor`
- contract / URL / header / path: deployed `NEXT_PUBLIC_*` values, Cognito callback/public URL, and a live environment where the judge path can sign in as tenant-a then tenant-b against real data

## Blocked on

`Trevor`

## Contract reminder

Detail stays on `?trace_id=` and not dynamic `[id]` routes. Day 1 keeps fixture integrity explicit; Day 2 live reads stay on `GET /v1/traces*` and `GET /v1/traces/{trace_id}/audit` with Cognito ID token handling and repo-owned env names only.
