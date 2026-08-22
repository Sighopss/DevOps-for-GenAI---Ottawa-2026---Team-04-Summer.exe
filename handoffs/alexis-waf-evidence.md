# Handoff — `alexis-wafdocs` — `waf-evidence`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-wafdocs`
- Branch: `alexis/docs/waf-evidence`
- Closes the last open box on #116. Evidence for #100 (already closed).

## Claimed paths

```
docs/RED_TEAM.md
docs/DATA_AND_ABUSE.md
docs/DEMO_SCRIPT.md
SECURITY.md          (perimeter row + honest summary)
GOVERNANCE.md        (two WAF lines)
AI_USAGE.md          (the vault sentence only)
handoffs/alexis-waf-evidence.md
```

## The finding: WAF *is* working — my earlier "it isn't" was a measurement error

I reported WAF as not evaluating four times (+4, +7, +9, +11 min). That was wrong, and worth recording because both causes are traps:

**1. I queried the wrong CloudWatch dimension.** I used `WebACL=tracevault-dev-api`, which is the `visibility_config.metric_name`. The actual `WebACL` dimension value is the ACL **name**, `tracevault-dev-cdn`. Querying by metric name returns zero datapoints and looks exactly like a dead WAF. Listing metrics dimension-agnostically is what exposed it.

**2. A WAF block does not surface as `403` on this distribution.** The distribution maps `403 → 200 /index.html` (and `404 → 200`) as the SPA fallback for client-side routing. That rewrite also catches WAF's 403, so a blocked attack returns `200` with the normal welcome page. My curl-based checks were therefore meaningless on their own.

### Actual evidence (window ending 2026-08-22 19:17Z)

| Metric — `AWS/WAFV2`, `WebACL=tracevault-dev-cdn` | Value |
|---|---|
| `AllowedRequests` (`Rule=ALL`) | **126** |
| `BlockedRequests` (`Rule=ALL`) | **9** |
| → `CrossSiteScripting_QUERYARGUMENTS` | **7** |
| → `GenericLFI_QUERYARGUMENTS` | **2** |

Those 9 blocks are the XSS and path-traversal payloads I fired at the edge, against `arn:aws:cloudfront::…:distribution/E36O2CPBDB3UPT`. WAF is evaluating real traffic and blocking on the managed rule group.

## What I shipped

Every "WAF filters nothing / is inert / not in force" claim I own is now corrected — **and deliberately not overcorrected**. The distinction the docs now draw everywhere:

> WAF guards the **Explorer** (CloudFront) and is demonstrably blocking. It does **not** guard `POST /v1/traces` — WAFv2 cannot attach to an HTTP API — so the ingest flood bound is still the in-Lambda caps + gateway throttling, exactly as before.

That distinction matters: "WAF is on" must not be read as "ingest is rate-limited". Files: `docs/RED_TEAM.md` (finding rewritten + new **WAF evidence** section with reproduction), `docs/DATA_AND_ABUSE.md` (abuse case 4 + both accepted-risk mentions), `SECURITY.md` (perimeter row + honest summary), `GOVERNANCE.md` (two lines), `docs/DEMO_SCRIPT.md` (honesty callout), `AI_USAGE.md` (vault sentence: 83 → 115 tests, read path is implemented and deployed).

Also corrected stale counts: `SECURITY.md` header `109 → 115`.

**Demo note added:** do not demo WAF by curling a payload and pointing at the status code — it reads `200`. Show the `BlockedRequests` metric.

## Left alone on purpose

- **`README.md` P-15 block (lines ~150–157)** still says "no flight has been ingested", "tenant isolation has not been demonstrated", and "WAF filters nothing". All three are now false. That block is **#122, Trevor's**, so I did not touch it — flagging it here and on the issue instead. My own README limitations line (from #55) is updated.
- `SECURITY.md` perimeter row is Trevor's by owner column, but it asserted a now-false security fact and I hold the evidence, so I corrected it and marked it `Trevor, verified by Alexis`.
- The ACL's `visibility_config.metric_name` is still `tracevault-dev-api`. Renaming churns the metric series; the docs now just say which dimension to query.

## Blocked on

`nobody`. Trevor merges.
