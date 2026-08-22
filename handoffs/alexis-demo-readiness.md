# Handoff — `alexis-spafix` — `demo-readiness`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-spafix`
- Branch: `alexis/infra/spa-routing`
- **Needs Trevor to apply** — my IAM cannot write Cognito (details below).

## Claimed paths

```
infra/cognito.tf
docs/DEMO_SCRIPT.md
handoffs/alexis-demo-readiness.md
```

## The sign-in bug — root-caused, fix written, apply blocked on IAM

The hosted UI fails with *"An error was encountered with the requested page."* Two independent causes, both in `infra/cognito.tf`:

**1. Flow mismatch.** The client is `allowed_oauth_flows = ["code"]`, but the Explorer is a static export with no server to hold a secret — `web/src/lib/cognito.ts` requests `response_type=token` and reads the ID token out of the URL fragment (`persistIdTokenFromHash`). Cognito rejects an implicit request against a code-only client. This alone is enough to produce that error page.

**2. `redirect_uri` mismatch.** `web/src/app/page.tsx` sends `redirect_uri = <origin>/explorer` (no trailing slash). The live client registers `<origin>` and `<origin>/explorer/` — **with** a slash. Cognito matches these strings exactly, so `/explorer` is not registered. Fixed by registering all three forms rather than swapping one for another, so this cannot regress on whichever spelling the app uses.

Implicit puts the token in the URL fragment, which is weaker than code + PKCE. That is an accepted trade for a 48h demo with two seeded tenants and a 7-day TTL; the durable fix is PKCE in the web app, which is a `web/` change and Michael's lane.

### Why I could not apply it

```
AccessDeniedException: User: arn:aws:iam::887991000498:user/team/tracevault-alexis
is not authorized to perform: cognito-idp:UpdateUserPoolClient
```

`tracevault-dev-terraform-ops` covers S3 state, DynamoDB locks, and CloudFront/WAFv2/ACM — not Cognito writes. Plan is clean (`0 to add, 2 to change, 0 to destroy`); the apply failed at the AWS call, so **nothing changed and the state lock released cleanly** — I verified both (0 active locks, client still `["code"]`).

Either apply this yourself, or add `cognito-idp:UpdateUserPoolClient` on this pool to my policy and I will.

## A stale lock I cleared (disclosure)

A `plan` lock from `DESKTOP-89H9R5F\Topfloorboss` had been held **~30 minutes** (since 19:16:48Z). Per #116 I do not force-unlock a live apply — but this was `OperationTypePlan`, which mutates nothing, and it was blocking all work. Alexis (human) authorised the unlock. `terraform force-unlock a0bc2c57-a4f1-3c6e-bfac-d4790e0f7d89`. If you had a plan genuinely running then, it died — sorry, and it is worth checking why a plan hangs that long on that box, since that is the whole reason #116 exists.

## What I did *not* change, and why

I built a CloudFront Function to rewrite directory URLs to `index.html`, because `/explorer/` was serving the 5.8 KB welcome page instead of the 18 KB Explorer. **Then I deleted it**: re-tested cache-busted, and `/explorer` and `/explorer/` both serve the real Explorer now. My earlier reading was a **cached 404-rewrite** from before the 19:13:56Z web-sync uploaded `explorer/index.html`. No function is needed, so none was added — recording it here so nobody re-derives the same false lead.

## Demo readiness (verified live, this session)

| Beat | State |
|---|---|
| Welcome page | Works — `/` 200 |
| Explorer, fixture mode | **Works** — `/explorer/` serves the real page with every judge beat: waterfall, `[EMAIL]`/`[SSN]`, `REDACTED`, `$0.0021`, 160 tokens, 7-day TTL, tenant switcher, 403 panel |
| Cognito sign-in | **Broken** until the fix above is applied |
| Explorer, live mode | **Broken** — `NEXT_PUBLIC_API_URL` not baked into the deployed build (#119, unassigned). Backend is fine; only the web build lacks the URL |
| Live API beats | All work — redaction, 403, list scoping, audit (`docs/RED_TEAM.md`) |
| Fallback recording | **Does not exist.** `docs/DEMO_SCRIPT.md` now carries two terminal fallbacks that need no video |

### Demo data seeded

Both tenants had presentation problems: tenant-a's list was red-team test junk with ugly ids, and **tenant-b's list was empty**, which would have made the isolation beat land on a blank screen. Seeded one clean flight each — `demoa0000000000000000000000000a1` and `demob0000000000000000000000000b1` — realistic span graphs, tokens and cost, PII planted and verified masked at rest.

`docs/DEMO_SCRIPT.md` rewritten around what actually works: which mode to demo and why, the verified prerequisites, a `curl` substitute for `scripts/demo_pii_flight.sh` (that script needs `uv`, which is not on this machine), and the fallbacks.

## Still open, not mine

- **#119** — bake `NEXT_PUBLIC_*` into the web build. This is the one gap between "fixture demo" and "live demo".
- **Dashboard interactivity** — reported as "nothing is clickable". Not root-caused: it needs browser devtools I do not have. The JS chunks all serve `200 application/javascript`, so it is not a load failure; the next thing to check is a hydration error in the console.

## Blocked on

Trevor: apply the Cognito change (or grant the IAM verb).
