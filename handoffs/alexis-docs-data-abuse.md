# Handoff — `alexis-docs` — `data-abuse`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-docs`
- Branch: `alexis/docs/data-and-abuse` (stacked on `alexis/read/flights`, PR #69 — every test the doc cites exists in-tree; auto-retargets as the stack merges)
- PR: TBD
- Mission file: issue #39 (Discover gate), assigned to Alexis

## Claimed paths (collision)

```
docs/DATA_AND_ABUSE.md
handoffs/alexis-docs-data-abuse.md
```

## Do not touch

```
docs/ARCHITECTURE.md docs/AI_INVENTORY.md SECURITY.md GOVERNANCE.md   (Trevor #66)
sdk/ demo-app/ infra/ scripts/ .github/ Makefile vault-code web/
```

## Safe to run in parallel with

Everyone — two new files, no overlap with open PRs (#67, #68, #69).

## What I shipped

- `docs/DATA_AND_ABUSE.md`: data classification (five classes, enforced-by-code framing: no raw-prompt field exists and unknown fields are rejected, so unclassified data has nowhere to arrive), synthetic-PII note, retention (Dynamo/logs 7d, S3-unreachable-after-TTL), and the six required abuse cases — cross-tenant read, PII exfiltration, prompt injection, token burn, stolen ingest key, log scraping — each mapped to named tests (all ten verified present in-tree) or explicitly listed in the accepted-risks table (no per-tenant rate limit; no S3 lifecycle rule; own-tenant pollution until key rotation) with the production path for each.
- Cross-references ARCHITECTURE.md / SECURITY.md / GOVERNANCE.md rather than duplicating them.

## What I need

- from whom: **Trevor** — review the three accepted-risk calls (they touch infra posture); merge after #68 → #69. Closes #39 when merged.
- from whom: **Michael** — issue #62's UI-side leakage tests are the on-screen half of abuse case 3; the doc points at your lane for it.

## Blocked on

`nobody` for review; merge order #68 → #69 → this.

## Contract reminder

Documentation only — no code, no contract changes.