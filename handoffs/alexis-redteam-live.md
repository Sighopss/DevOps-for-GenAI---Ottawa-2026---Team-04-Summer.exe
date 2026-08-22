# Handoff — `alexis-redteam` — `live`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-redteam`
- Branch: `alexis/docs/red-team` (from main)
- PR: TBD
- Related: #54 (red team), #56 (demo script), #18 (live half)

## Claimed paths

```
docs/RED_TEAM.md
docs/redteam/redteam.sh
docs/DEMO_SCRIPT.md
handoffs/alexis-redteam-live.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
vault/ contracts/                                  (not this PR)
```

Note: put the harness under `docs/redteam/`, NOT `scripts/` (Trevor's lane).

## What I shipped

- `docs/RED_TEAM.md` — 13 unauthenticated/hostile-input attacks run **live** against the deployed API and captured (all fail-closed: gateway 401s, vault ingest byte-exact contract 401s, forged-JWT rejection, no CORS reflection, edge HSTS/CSP on errors), plus 5 authenticated attacks scaffolded (cross-tenant 403, live PII flight + at-rest check, list isolation, audit, injection). Includes the two infra findings from #76 as real red-team material (WAF inert, TLS floor TLSv1) with fix paths.
- `docs/redteam/redteam.sh` — runnable harness. Unauthenticated half verified green here (6/6). Authenticated half env-driven (`TENANT_A_KEY`, `TENANT_A_JWT`, `TENANT_B_JWT`), skips cleanly, no secret on disk.
- `docs/DEMO_SCRIPT.md` — the 3-minute judge-path runbook (roles, timings, honesty callouts, labelled fallback) for #56.

## What I need (relay to Trevor)

To fire the authenticated half (#54 B1–B5, #18 live) and record the demo:
1. **`tracevault-alexis` SECRET access key** — the screenshot showed only the key **ID** (`AKIA…`, account `887991000498`); the 40-char secret is required and is shown only once at create time. **Do not screenshot/paste the secret into Slack** — his own #74 handoff says off-repo, and a pasted secret must be deleted + re-minted. Send it so it can go straight into `~/.aws/credentials`.
2. **Tenant-key values** for `tenant-a` (and `tenant-b`) — the `X-Tenant-Key` the Secrets Manager map expects, for live ingest.
3. **Cognito passwords** for `tenant-a` and `tenant-b` — to mint ID tokens for the read/403 attacks.
4. (Michael) **publish the Explorer** — `/` is 403 until the web bucket is synced; the demo needs the UI.

## Blocked on

Credential handover (1–3 above) for the authenticated half. The report + harness + demo script stand on their own now.

## Contract reminder

Documentation + a test harness only. No code, no contract change.
