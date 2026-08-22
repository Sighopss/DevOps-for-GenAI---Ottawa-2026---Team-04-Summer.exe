# Handoff — michael-m7 — live-explorer-finish

- Date: 2026-08-22
- Human: Michael
- Agent id: `michael-m7`
- Branch: `michael/flight-explorer-fixtures`
- PR: `TBD`
- Mission / scope: Finish Michael's follow-up explorer work after the fixture PR: commit `PRODUCT.md` and `DESIGN.md`, wire live `GET /v1/traces*` + audit into `web/`, harden tenant switching and forbidden UI, and extend Playwright for fixture and live 403 coverage.

## Claimed paths (collision)

```
PRODUCT.md
DESIGN.md
web/
handoffs/michael-m7-live-explorer-finish.md
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

Trevor docs, infra, and CODEOWNERS PRs. Alexis vault/read/audit tests and docs. Any PR that does not claim `web/`, `PRODUCT.md`, or `DESIGN.md`.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Build`
- P-ids this PR moves: `P-11`, `P-15`
- Rubric rows (pts): `Engineering 15`, `Security 15`, `Presentation 5`
- Tests / attack shown: `web/node_modules/.bin/eslint.cmd src tests playwright.config.ts next.config.ts eslint.config.mjs`, `web/node_modules/.bin/next.cmd build`, `web/node_modules/.bin/playwright.cmd test --workers 1`
- Stub/live (P-15): Day 1 stays explicit on committed fixtures. Day 2 live reads now use `GET /v1/traces*` and `GET /v1/traces/{trace_id}/audit` when a Cognito ID token and `NEXT_PUBLIC_API_URL` are present. Final judge proof still needs Trevor's deployed values and live URL.
- Judge bar (`JUDGE.md`): never-kill intact. The UI keeps tokens in sessionStorage, never shows raw SSN/email, renders tenant mismatch as `403 forbidden` chrome instead of a blank 404-like state, and makes fixture-vs-live mode explicit.

## What I shipped

- files: `PRODUCT.md`, `DESIGN.md`, `web/` source, tests, and config
- outputs / env **names** (no secret values): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_DOMAIN`
- tests: fixture render, tenant-b masked fixture path, and live tenant-b forbidden read through mocked `GET /v1/traces*`

## What I need

- from whom: `Trevor`
- contract / URL / header / path: deployed `NEXT_PUBLIC_*` values, Cognito callback/public URL, and a live environment for the tenant-a then tenant-b judge path

## Blocked on

`Trevor`

## Contract reminder

Keep detail on `?trace_id=` only. Day 1 must stay honest about fixture-only data. Day 2 live reads stay on `GET /v1/traces*` and `GET /v1/traces/{trace_id}/audit` with Cognito ID token handling and repo-owned env names only.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and the ownership table in README.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
