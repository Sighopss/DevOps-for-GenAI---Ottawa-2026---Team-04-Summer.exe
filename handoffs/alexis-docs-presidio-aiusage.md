# Handoff — `alexis-docs2` — `presidio-aiusage`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-docs2`
- Branch: `alexis/docs/presidio-aiusage` (from main)
- Related: #84 (Presidio decision), #34 (AI_USAGE row)

## Claimed paths

```
AI_USAGE.md                    (my row only — the file invites each human to append their own)
docs/DATA_AND_ABUSE.md
handoffs/alexis-docs-presidio-aiusage.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
vault/ contracts/                                  (not this PR)
```

## What I shipped

- **#84 decision — Presidio declared absent.** Recorded the decision in `docs/DATA_AND_ABUSE.md`: deny-list is authoritative (deterministic, stdlib, in the Lambda, proven at rest); Presidio is not installed in CI or packaged in the zip, imported lazily, fail-closed if present. No judged behaviour depends on it. Consistent with the existing `docs/AI_INVENTORY.md` note. **Recommend closing #84** — the decision is "declare absent", not "integrate".
- **#34 — Alexis's AI_USAGE row** appended (my row only): Claude Code / Fable 5, per-mission agents, what the vault lane produced, and how I reviewed it (pytest+bandit, secret-scan every diff, live-AWS verification). #34 stays open until all three rows are in — Trevor's and Michael's are already present, so this completes the humans; a maintainer can close once satisfied.

## Blocked on

`nobody`. Trevor merges.
