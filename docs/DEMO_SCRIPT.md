# Three-minute demo script

Issue #56. The judge path from PLAN.md, timed and scripted, with a labelled fallback. Roles: **Driver** (screen + terminal), **Narrator**. Stubs named aloud where present.

- **API:** `https://55qm437628.execute-api.us-east-1.amazonaws.com` — live, verified
- **Explorer:** `https://d13b678j60bhap.cloudfront.net` — live, serving (200)
- **Users:** `tenant-a`, `tenant-b` (Cognito hosted UI; passwords held by the operator)

## Which mode you are demoing — read this first

The Explorer has two modes and **only one of them works today**.

| Mode | State | Use it? |
|---|---|---|
| **Fixture mode** ("Preview sample flight") | **Works.** Committed tenant-a flight + tenant-b isolation proof, rendered from `contracts/fixtures/`. Every judge beat is on the screen: waterfall, `[EMAIL]`/`[SSN]`, `REDACTED`, `$0.0021`, 160 tokens, 7-day TTL, tenant switcher, 403 panel. | **Yes — demo this.** |
| **Live mode** (after Cognito sign-in) | **Broken.** `NEXT_PUBLIC_API_URL` was not baked into the deployed build, so the Explorer throws a config error instead of listing flights (issue #119). Sign-in itself works. | No, until #119 lands. |

The backend is *not* the problem — the API serves live flights correctly (proven in `docs/RED_TEAM.md`). Only the web build is missing the URL. If #119 lands before the demo, live mode becomes available and the script below works unchanged; if it does not, run fixture mode and say so out loud.

## Prerequisites (before the clock)

- [x] Explorer published — `/` returns 200 with the welcome page
- [x] Both Cognito users can sign in (verified by minting ID tokens for both)
- [x] Live demo data seeded — a clean tenant-a flight (`demoa0000000000000000000000000a1`) and a tenant-b flight (`demob0000000000000000000000000b1`), both with PII masked at rest, so neither tenant's list is empty
- [ ] **Deep links:** `/explorer/` must serve the Explorer, not the welcome page. Fixed by the CloudFront index-rewrite function in this PR — re-verify with `curl -s https://d13b678j60bhap.cloudfront.net/explorer/ | wc -c` (expect ~18000, **not** ~5800)
- [ ] Fallback recording rendered and labelled (see end)

### Live-flight command (substitute for `scripts/demo_pii_flight.sh`)

`scripts/demo_pii_flight.sh` needs `uv` and the `demo-app` toolchain. If that is not on the demo machine, this reproduces the same beat — a live flight carrying PII, masked on arrival — with nothing but `curl`:

```bash
curl -s -X POST "$TRACEVAULT_API/v1/traces" \
  -H "X-Tenant-Key: $TENANT_A_KEY" -H 'content-type: application/json' \
  -d '{"spans":[{"trace_id":"live0000000000000000000000000001","span_id":"1111111111111111",
       "tenant_id":"tenant-a","kind":"llm","name":"demo.converse","status":"ok",
       "start_time":"2026-08-22T19:00:00.000Z","end_time":"2026-08-22T19:00:01.000Z",
       "cost_usd":0.0021,"prompt_preview":"Customer jane.doe@example.com SSN 123-45-6789 asks about retention"}]}'
# -> 202 {"accepted":true,...}, then read it back and the prompt shows [EMAIL] / [SSN]
```

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
- **WAF guards the Explorer, not the API.** It is attached to CloudFront and blocking (evidence in `docs/RED_TEAM.md`), but WAFv2 cannot attach to an HTTP API, so ingest flood protection is the in-Lambda caps + gateway throttling. Also: a WAF block returns `200` here, not `403`, because the distribution rewrites `403 -> /index.html` for SPA routing — don't demo it by status code.
- **TLS floor is TLSv1** at the edge (default cert); custom-domain + ACM is the fix. Named in `docs/RED_TEAM.md`.

## Fallbacks — in the order you should reach for them

**No recording exists yet.** Someone has to record one; until then the terminal fallback below is the safety net, and it is arguably the stronger proof anyway because it is live.

### Fallback 1 — terminal (works whenever the API is up, no UI needed)

`docs/redteam/redteam.sh` *is* the demo, in evidence form. With the three env vars exported it walks the same four beats and prints pass/fail:

```bash
TENANT_A_KEY=… TENANT_A_JWT=… TENANT_B_JWT=… bash docs/redteam/redteam.sh
# 14/14 — ingest accepted, prompt masked at read, cross-tenant 403, tenant-b list clean, audit row written
```

Narrate it as: *"Same four beats the screen shows, asserted against the live system — you can watch them pass."* Mint the JWTs with `aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH` (client id `6obn55hg3acb4vnqleua1prru2`).

The single cheapest live proof, if everything else is down: `curl https://55qm437628.execute-api.us-east-1.amazonaws.com/health` → `{"ok":true}`.

### Fallback 2 — the four beats as raw curl

If the harness is unavailable, each beat is one command. Run them in this order and the story still lands:

```bash
API=https://55qm437628.execute-api.us-east-1.amazonaws.com
# 1. redaction: read a seeded flight, prompt comes back masked
curl -s "$API/v1/traces/demoa0000000000000000000000000a1" -H "Authorization: Bearer $TENANT_A_JWT"
# 2. isolation: tenant-b asks for tenant-a's trace -> 403 "tenant mismatch"
curl -s -w '\n%{http_code}\n' "$API/v1/traces/demoa0000000000000000000000000a1" -H "Authorization: Bearer $TENANT_B_JWT"
# 3. list scoping: tenant-b sees only its own flight
curl -s "$API/v1/traces" -H "Authorization: Bearer $TENANT_B_JWT"
# 4. audit: opening the trail writes a row and returns it
curl -s "$API/v1/traces/demoa0000000000000000000000000a1/audit" -H "Authorization: Bearer $TENANT_A_JWT"
```

### Fallback 3 — recording

If one gets made: play `demo-fallback.mp4` labelled on-screen **"Pre-recorded — <date>, same commit as live"**. Never present a recording as live.
