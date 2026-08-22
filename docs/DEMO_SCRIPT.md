# Three-minute demo script

Issue #56. The judge path from PLAN.md, timed and scripted, with a labelled fallback. Roles: **Driver** (screen + terminal), **Narrator**. Stubs named aloud where present.

- **API:** `https://55qm437628.execute-api.us-east-1.amazonaws.com`
- **Explorer:** `https://d13b678j60bhap.cloudfront.net` — live (200) as of 2026-08-22. Start from `/`, not a bookmarked `/explorer`: direct navigation to `/explorer` (no extension) falls back to the welcome page instead of the flight explorer today, only in-app navigation reaches it (or the exact URL `/explorer.html`).
- **Users:** `tenant-a`, `tenant-b` (Cognito hosted UI; passwords held by the operator)

## Prerequisites (before the clock)

- [ ] Explorer reachable: `curl -so /dev/null -w '%{http_code}' https://d13b678j60bhap.cloudfront.net/` → `200` (it has been live since 2026-08-22; re-check anyway, an apply can regress it)
- [ ] Both Cognito users can sign in
- [ ] One tenant-a flight with PII already ingested (so the screen isn't empty): run `TENANT_A_KEY=… bash docs/redteam/redteam.sh` or `scripts/demo_pii_flight.sh`
- [ ] Fallback recording rendered and labelled (see end)

## Script (3:00)

**0:00–0:25 — The problem (Narrator, title slide)**
"Every AI request is a black box — prompts, tool calls, cost, errors. Teams log the raw prompt to see inside, and now their observability store *is* the PII leak. TraceVault records the whole flight and stores none of the sensitive text. Live on AWS, two tenants, right now."

**0:25–1:05 — One flight (Driver: sign in as tenant-a → flight list → waterfall)**
- Sign in at the hosted UI as **tenant-a**. "Real Cognito, `custom:tenant_id` on the ID token."
- Open the flight. "One request = one trace: the HTTP root, a RAG retrieve, a tool call, the LLM answer — parent/child, latency, tokens, and a dollar cost per flight."

**1:05–1:45 — The governance moment (Driver: point at the masked prompt + badge)**
- "This flight's prompt contained an email and an SSN." Point at `prompt_preview`: **`[EMAIL]` / `[SSN]`**, the `REDACTED` badge, the `prompt_hash`.
- "The raw text was never stored. Redaction happens at ingest, fail-closed — if we can't mask it, we store nothing and return 400. What's on disk is the hash and the masked preview." (Optional, if `tracevault-alexis` key is handy: `aws dynamodb get-item …` live to show no raw SSN at rest.)

**1:45–2:20 — Tenant isolation (Driver: switch to tenant-b)**
- Sign in as **tenant-b**. "Same product, different tenant."
- Paste tenant-a's `trace_id` into the URL / switcher. **403 — `tenant mismatch`.** "Not a 404 that hides it — a deliberate 403. And tenant-a's flight is absent from tenant-b's list. Isolation is a test a judge can watch fail."

**2:20–2:45 — Audit (Driver: audit strip)**
- "Every open is audited — who, which trace, when. TTL is 7 days; nothing lingers." Show the audit row(s).

**2:45–3:00 — Close (Narrator)**
- "Write-time redaction, tenant isolation, audited access — a flight recorder that can't become the leak. All on AWS behind one HTTPS URL." Show the API URL / `curl /health` → `{"ok":true}`.

## Honesty callouts (say these; do not let a judge catch them)

- **Bedrock is stubbed** for the demo flight (`TRACEVAULT_FAKE_BEDROCK`) — the span *shape* and redaction are real, the model call is faked to stay in budget.
- **WAF is attached to CloudFront but not yet confirmed filtering traffic** (fixed #100/#128 same day; a deliberate bad request had not yet been observed blocked as of this writing). Flood protection until confirmed is the in-Lambda caps + gateway throttling. Named in `docs/RED_TEAM.md`.
- **TLS floor is TLSv1** at the edge (default cert); custom-domain + ACM is the fix. Named in `docs/RED_TEAM.md`.

## Fallback recording

If live fails: play `demo-fallback.mp4`, labelled on-screen **"Pre-recorded — <date>, same commit as live"**. Never present a recording as live. The `curl /health` → `{"ok":true}` step is the cheapest live proof if only the UI is down.
