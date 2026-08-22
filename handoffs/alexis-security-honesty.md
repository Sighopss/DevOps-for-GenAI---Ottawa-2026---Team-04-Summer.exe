# Handoff — `alexis-sec` — `security-honesty`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-sec`
- Branch: `alexis/docs/security-honesty` (from main)
- Closes: #95, #96, #97 (vault security-doc honesty pass)

## Claimed paths

```
docs/RED_TEAM.md
docs/redteam/redteam.sh
SECURITY.md            (Alexis-owned vault rows + honest summary only)
docs/DATA_AND_ABUSE.md
handoffs/alexis-security-honesty.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
vault/ contracts/                                  (not this PR — code unchanged)
```

Note: SECURITY.md is Trevor-seeded; I edited only the vault-owned rows and the honest-summary, matching the #96 assignment (same pattern as his #76 honesty pass). Left Trevor's infra rows (Perimeter/WAF, IAM, at-rest infra) as his.

## What I shipped

- **#95** — `docs/RED_TEAM.md` authenticated section rewritten from "scaffolded" to a **captured-live B1-B5 table** (cross-tenant 403, live PII masked at read + at rest via direct S3/Dynamo read, tenant-b list isolation, audit oldest-first, log hygiene 0 hits). Root cause of the gap: my capture + harness-fix commits from PR #90 didn't survive the merge (only the first commit landed). Also **re-applied the harness fix** — `docs/redteam/redteam.sh` on main was the broken version (asserted vs a never-ingested fixture trace, wrong spacing, broken lookahead greps). It now ingests its own trace then attacks it: **14/14 live** (re-run today with fresh tokens).
- **#96** — `SECURITY.md` vault rows corrected: cross-tenant read and unaudited-access no longer say "not implemented / largest open gap" (they're implemented, tested, and proven live); at-rest and logs rows gained live-proof pointers; test count 83→109; Presidio row says "not shipped in prod, deny-list authoritative (#84)"; honest-summary rewritten from "unproven in operation" to "demonstrated in operation," with the WAF/TLS infra caveats kept; stale "no terraform apply has run" corrected.
- **#97** — `docs/DATA_AND_ABUSE.md` abuse case 4 + both accepted-risk mentions: WAF stated **inert**, in-Lambda caps named as the active flood bound, no claim WAF protects ingest. Cap/adversarial tests still green (20 passed).

## Verification

- `python -m pytest vault` → 109 passed; cap/adversarial subset 20 passed.
- `bash docs/redteam/redteam.sh` with live creds → 14/14.
- Secret-scan on the diff: clean (only synthetic PII / AWS doc-example key).

## Depends on / for Trevor

WAF-attach-to-CloudFront is the infra fix #97's residual risk waits on — Trevor's issue. TLS floor (custom domain + ACM) likewise. Neither is vault work.

## Blocked on

`nobody`. Trevor merges.
