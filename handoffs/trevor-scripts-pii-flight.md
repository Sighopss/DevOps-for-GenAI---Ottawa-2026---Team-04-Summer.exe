# Handoff — trevor-scripts — pii-flight

- Date: 2026-08-21
- Human: Trevor
- Agent id: trevor-scripts
- Branch: trevor/scripts/pii-flight
- PR: TBD
- Mission file: `skills/trevor-recorder/agents/scripts.md`

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
scripts/
handoffs/trevor-scripts-pii-flight.md
```

## Do not touch

```
demo-app/
sdk/
vault/
web/
infra/
.github/
Makefile
contracts/
PRODUCT.md
DESIGN.md
```

## Safe to run in parallel with

`trevor-demo` (#30), `trevor-sdk` (#28), `trevor-ci` (#27), `trevor-infra` (#29), `trevor-contracts` (#26). Not with another `trevor-scripts` writer.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Build`
- P-ids this PR moves: `P-04`, `P-15`
- Rubric rows (pts): `Presentation 5`
- Tests / attack shown: script requires `--pii` path (synthetic email/SSN in the demo prompt). Does not curl vault with raw PII. Does not echo keys.
- Stub/live (P-15): `TRACEVAULT_FAKE_BEDROCK=1` is valid for CI / no-AWS. Unset the flag for live Bedrock. Missing `demo-app/` → exit 2 naming `trevor-demo` until #30 merges.

## What I shipped

- files:
  - `scripts/demo_pii_flight.sh`
  - `scripts/check_unix.sh`
  - `handoffs/trevor-scripts-pii-flight.md`
- outputs / env **names** (no secret values):
  - `TRACEVAULT_TENANT_ID`
  - `TRACEVAULT_INGEST_URL`
  - `TRACEVAULT_FAKE_BEDROCK`
- tests: `check_unix.sh` (grep/sed/awk). Judge script needs `demo-app/` from #30.

## What I need

- from whom: trevor-demo (#30) for `python -m demo_app.main`
- contract / URL / header / path: `uv run python -m demo_app.main --pii --tenant tenant-a --question "What is retention?"`

## Blocked on

`trevor-demo` (#30) until `demo-app/` is on `main`.

## Contract reminder

Judge button only. Unix. No PowerShell. No secrets in argv or echo. Ingest is `X-Tenant-Key`, not Cognito.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
