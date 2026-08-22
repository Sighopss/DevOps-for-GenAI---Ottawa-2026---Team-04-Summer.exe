# Handoff — `alexis-redact` — `fail-closed`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-redact`
- Branch: `alexis/redact/fail-closed`
- PR: TBD
- Mission file: `skills/vault/agents/redact.md` (scratchpad; issue #12 in this repo)

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
vault/__init__.py
vault/.bandit
vault/redact/
vault/tests/
handoffs/alexis-redact-fail-closed.md
```

## Do not touch

```
sdk/ demo-app/ infra/ scripts/ .github/ Makefile   (Trevor)
web/ PRODUCT.md DESIGN.md                          (Michael)
contracts/                                         (hour 0 — PR #26, all three)
```

## Safe to run in parallel with

Any agent not writing `vault/` or this handoff file: `trevor-infra` (#29), `trevor-demo` (#30), `trevor-scripts` (#31), `trevor-docs` (#37), Michael's `web/` work. NOT safe with another vault agent.

## What I shipped

- files: `vault/redact/{__init__,models,denylist,engine}.py`, `vault/tests/redact/{test_denylist,test_engine,test_no_raw_leak,test_fail_closed}.py`, `vault/.bandit`, package `__init__.py`s.
- behavior: `redact(text) -> RedactResult(prompt_hash, prompt_preview, safe, findings, presidio_used)` and `redact_strict()` raising `RedactionError` (ingest will map it to `400 redaction_failed`, nothing stored). Deny-list (deterministic, stdlib-only, contractual): EMAIL → `[EMAIL]`, SSN → `[SSN]`, AKIA/ASIA keys → `[AWS_KEY]`, `sk-` → `[API_KEY]`. Tokens for EMAIL/SSN match `contracts/fixtures/*` and `sdk/src/tracevault/redact_hint.py`. Hash = sha256 hex (64) of the original. Preview capped at 200 (schema `maxLength`). Presidio is optional + lazy: not installed → deny-list-only (CI installs only pytest+bandit; judge-path guarantees do not depend on Presidio); installed but failing mid-analysis → fail closed. Residual-PII double check: if a deny-list pattern survives masking, `safe=False`, preview empty. No third-party imports at module load — `python -m pytest vault` passes on a bare pytest install.
- tests: 23 passed (`python -m pytest vault`). `bandit -r vault -x "*/tests/*"` → 0 issues. Includes: unicode-local-part email masks (`usagé@exemple.fr` — ASCII-only regex missed it, widened to `\w`), no raw PII in stdout/logging/repr, fail-closed on presidio failure and on residual PII, error text never carries PII.

## What I need

- from whom: **Trevor (`trevor-ci`)** — `vault.yml` runs `bandit -r vault`, which exits 1 on B101 (pytest asserts in `vault/tests/`). One-line fix, verified locally on bandit 1.9.4: `bandit -r vault -x "*/tests/*"` (or `--ini vault/.bandit`, same exclusion). Until then the vault check is red on any vault PR.
- from whom: **Trevor (`trevor-ci`)**, later — when `alexis-ingest` lands, `vault.yml` must also `pip install -r vault/requirements.txt` (boto3 etc.); today vault is stdlib-only on purpose.
- from whom: **Trevor (contracts PR #26)** — `contracts/http.md` says fixture names are locked including `tenant-b-forbidden.json`, but issue #33 renames it `tenant-b-pii.json` (PLAN.md's name). One of the two must win before Michael reads fixtures. Contract content otherwise reviewed by Alexis: schema, error JSON, ID-token note, mask tokens all check out — approve from me.

## Blocked on

`nobody` — for merge: Trevor review + the `vault.yml` bandit flag (or accept a red bandit check until his CI tweak).

## Contract reminder

`vault.redact.redact_strict(prompt)` is the only path ingest may use to produce `prompt_hash` / `prompt_preview`; on `RedactionError` respond `400 {"error":{"code":"redaction_failed",...}}` and store nothing. Downstream may rely on: preview ≤ 200 chars, hash = 64 lowercase hex, tokens `[EMAIL] [SSN] [AWS_KEY] [API_KEY] [REDACTED]`.