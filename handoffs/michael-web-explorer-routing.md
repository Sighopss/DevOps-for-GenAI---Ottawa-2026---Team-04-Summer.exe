# Handoff — michael-web-explorer-routing — CDN directory-index shims

- Date: 2026-08-22
- Human: Michael
- Agent id: michael-web-explorer-routing
- Branch: michael/web-explorer-routing
- PR: TBD
- Mission / scope: Make welcome CTAs (`Preview sample flight`, Cognito return to `/explorer/`) land on the explorer on CloudFront+S3, and keep that working after `s3 sync --delete`.

## Claimed paths (collision)

```
web/
.github/workflows/deploy.yml
handoffs/michael-web-explorer-routing.md
```

## Do not touch

```
vault/
sdk/
demo-app/
infra/
scripts/
contracts/
```

## Safe to run in parallel with

Alexis vault work. Trevor docs PRs that do not edit `deploy.yml` web-sync.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: Validate, Deploy
- P-ids this PR moves: P-06, P-11, P-15
- Rubric rows (pts): Engineering 15, Presentation 5, Reliability & Observability 10
- Tests / attack shown: live curl of `/`, `/explorer`, `/explorer/` after shim publish; `pnpm lint` / Playwright when CI runs
- Stub/live (P-15): fixture mode remains honest; live Cognito path uses `/explorer/`
- Judge bar (`JUDGE.md`): never-kill intact — no localStorage, masked prompts, tenant-b 403 chrome

## What broke

Next `trailingSlash: true` already published `explorer/index.html`. CloudFront origin is S3 REST + OAC (no website IndexDocument). Requests to `/explorer` and `/explorer/` 403/404, then `custom_error_response` remapped them to welcome `index.html`. CTAs looked dead: same welcome page again. `/explorer/index.html` was already correct.

CSP was fine (`script-src 'self' 'unsafe-inline'`).

## What I shipped

- files: operate redesign already on this branch (`trailingSlash`, `/explorer/` links, Cognito code flow); `web/scripts/publish-explorer-cdn-keys.sh`; deploy sync calls the shim after `--delete`
- live hotfix (already applied): put-object keys `explorer` and `explorer/` from `explorer/index.html`, invalidate `E36O2CPBDB3UPT`
- outputs / env names: none new
- tests: live curl proof below

## What I need

- from whom: Trevor — keep Cognito callback allowlist including `https://d13b678j60bhap.cloudfront.net/explorer/`; optional later CF Function so shims are unnecessary
- contract / URL / header / path: canonical explorer URL stays `/explorer/`

## Blocked on

nobody for CTA hard-nav. Trevor only if Cognito callback is still bare `/` or missing `/explorer/`.

## Contract reminder

Detail stays on `?trace_id=`. Tokens in `sessionStorage` only. Do not delete SPA error responses without a Function rewrite plan.

## Verify

```bash
curl -sI https://d13b678j60bhap.cloudfront.net/explorer/ | head
# Content-Length must match explorer (~18k), not welcome (~5.8k)
curl -s https://d13b678j60bhap.cloudfront.net/explorer/ | grep -o 'explorer-shell\|welcome-shell'
# expect explorer-shell only
```
