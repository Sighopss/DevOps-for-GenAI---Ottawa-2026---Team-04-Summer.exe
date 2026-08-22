# Handoff — michael-m7 — live-explorer-finish

- Date: 2026-08-22
- Human: Michael
- Agent id: `michael-m7`
- Branch: `michael/flight-explorer-fixtures`
- PR: `#88`
- Mission / scope: Finish Michael's follow-up explorer work after the fixture PR: commit `PRODUCT.md` and `DESIGN.md`, wire live `GET /v1/traces*` + audit into `web/`, harden tenant switching and forbidden UI, align hosted Cognito sign-in with the live `code` flow + root callback, extend Playwright for fixture/live/error-state coverage, and append Michael's AI usage disclosure.

## Claimed paths (collision)

```
PRODUCT.md
DESIGN.md
web/
AI_USAGE.md
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
```

## Safe to run in parallel with

Trevor docs, infra, and CODEOWNERS PRs. Alexis vault/read/audit tests and docs. Any PR that does not claim `web/`, `PRODUCT.md`, `DESIGN.md`, or `AI_USAGE.md`.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Build`, `Validate`, `Govern`
- P-ids this PR moves: `P-06`, `P-11`, `P-15`
- Rubric rows (pts): `Engineering 15`, `Security 15`, `Reliability & Observability 10`, `Presentation 5`
- Tests / attack shown: `web/node_modules/.bin/eslint.cmd src tests playwright.config.ts next.config.ts eslint.config.mjs`, `web/node_modules/.bin/next.cmd build`, `web/node_modules/.bin/playwright.cmd test --workers 1`
- Stub/live (P-15): Day 1 stays explicit on committed fixtures and uses `tenant-a-rag.json` as the only regular flight fixture; tenant-b gets the locked 403 contract example only. Day 2 live reads now use `GET /v1/traces*` and `GET /v1/traces/{trace_id}/audit` when a Cognito ID token and `NEXT_PUBLIC_API_URL` are present. Final judge proof still needs Trevor's deployed values and live URL.
- Judge bar (`JUDGE.md`): never-kill intact. The UI keeps tokens in sessionStorage, never uses localStorage, never shows raw SSN/email, renders tenant mismatch as contracted `403` chrome instead of a blank 404-like state, and makes fixture-vs-live mode explicit.

## What I shipped

- files: `PRODUCT.md`, `DESIGN.md`, `AI_USAGE.md`, `web/` source, tests, and config
- outputs / env **names** (no secret values): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_DOMAIN`
- tests: fixture render, tenant-b Day 1 honesty + locked 403 contract path, live operator detail/error span path, live tenant-b forbidden read through mocked `GET /v1/traces*`, trace-not-found UI, API-unreachable UI, and hosted Cognito code callback into the live Explorer path

## What I need

- from whom: `Trevor`
- contract / URL / header / path: deployed `NEXT_PUBLIC_*` values, Cognito callback/public URL, and a live environment for the tenant-a then tenant-b judge path. `README.md` mirror text for the elevator pitch is still Trevor-owned and currently overlaps Trevor PR `#76`.

## Blocked on

`Trevor` for deployed public URL / runtime values. `nobody` for the remaining repo-owned Michael work in this PR.

## Contract reminder

Keep detail on `?trace_id=` only. Day 1 must stay honest about fixture-only data. Day 2 live reads stay on `GET /v1/traces*` and `GET /v1/traces/{trace_id}/audit` with Cognito ID token handling and repo-owned env names only. Hosted sign-in now matches the current Cognito app client by using the `code` flow and the root callback URL, then forwarding into `/explorer`. Do not mirror product copy into `README.md` until Trevor's overlapping docs PR is resolved.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and the ownership table in README.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
