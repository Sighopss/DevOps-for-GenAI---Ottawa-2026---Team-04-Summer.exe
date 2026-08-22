# Handoff — michael-107 — operate-redesign

- Date: 2026-08-22
- Human: Michael
- Agent id: `michael-107-operate-redesign`
- Branch: `michael/107-operate-redesign`
- PR: `TBD`
- Mission / scope: Rework the exported `web/` operator flow around the new Michael operate/design issues by making `/explorer/` the static route, tightening the welcome gate, replacing the dashboard-style explorer with an operator-first reconstruction view, and keeping the hosted Cognito handoff, governance chrome, and no-raw-PII guarantees intact.

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
DESIGN.md
web/
handoffs/michael-107-operate-redesign.md
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
PRODUCT.md
AI_USAGE.md
```

## Safe to run in parallel with

Trevor infra, docs, and deployment-support work that does not claim `web/`, `DESIGN.md`, or this handoff. Alexis vault/read/audit work and any PR that stays out of the claimed paths above.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Design`, `Build`, `Validate`, `Deploy`
- P-ids this PR moves: `P-11`, `P-15`
- Rubric rows (pts): `Engineering 15`, `Security 15`, `Reliability & Observability 10`, `Presentation 5`
- Tests / attack shown: `web/node_modules/.bin/eslint.cmd src tests playwright.config.ts next.config.ts eslint.config.mjs`, `web/node_modules/.bin/next.cmd build`, `web/node_modules/.bin/playwright.cmd test --workers 1`
- Stub/live (P-15): Fixture mode remains explicit and live mode remains explicit. The exported app still reconstructs detail through `?trace_id=` only, keeps tenant mismatch on intentional `403` chrome, and uses the Cognito/public API env names rather than hardcoded URLs. This handoff deploys the current exported web bundle to the existing CloudFront path.
- Judge bar (`JUDGE.md`): never-kill intact. Raw SSN/email still stay off-screen, tokens stay in memory/sessionStorage rather than git, the operator path still fails closed on forbidden cross-tenant reads, and the root route remains a sign-in gate rather than a fake marketing site.

## What I shipped

- files: `DESIGN.md`, `web/` source, tests, config, and the enterprise mark asset in `web/public/tracevault-enterprise.png`
- outputs / env **names** (no secret values): `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_COGNITO_REGION`, `NEXT_PUBLIC_COGNITO_USER_POOL_ID`, `NEXT_PUBLIC_COGNITO_CLIENT_ID`, `NEXT_PUBLIC_COGNITO_DOMAIN`
- tests: exported `/explorer/` route build, hosted Cognito callback route handling, fixture/live explorer states, forbidden chrome, governance visibility, and no-raw-PII fixture coverage through Playwright plus lint/build

## What I need

- from whom: `Trevor`
- contract / URL / header / path: final PR merge on Trevor's side. If Cognito callback URLs or CSP headers drift again, they must still keep `/` and `/explorer/` valid on the deployed CloudFront origin.

## Blocked on

`nobody`

## Contract reminder

Keep the web lane on exported Next.js App Router pages only, with detail selected by `?trace_id=` rather than dynamic `[id]` routes, and keep governance/redaction/tenant surfaces visible without exposing raw prompt or PII content.
