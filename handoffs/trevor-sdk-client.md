# Handoff — trevor-sdk — client

- Date: 2026-08-21
- Human: Trevor
- Agent id: trevor-sdk
- Branch: trevor/sdk/client
- PR: https://github.com/Sighopss/DevOps-for-GenAI---Ottawa-2026---Team-04-Summer.exe/pull/28
- Mission file: `skills/trevor-recorder/agents/sdk.md`

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
sdk/
handoffs/trevor-sdk-client.md
```

## Do not touch

```
vault/
web/
demo-app/
infra/
scripts/
.github/
Makefile
PRODUCT.md
DESIGN.md
contracts/
assets/
```

## Safe to run in parallel with

`trevor-infra`, `trevor-ci`, Alexis vault missions, Michael web missions. Not with another `trevor-sdk` writer.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: Build
- P-ids this PR moves: P-09, P-10
- Rubric rows (pts): Engineering 15
- Tests / attack shown: golden required keys; http→rag+llm nesting (same `trace_id`, `parent_id`); `sensitive=True` prompt with email+SSN never appears in logs/stdout/`prompt_preview`
- Stub/live (P-15): unit tests only; no Bedrock; ingest unset → `sdk/.last-flight.json` (live POST when `TRACEVAULT_INGEST_URL` is set)
- Judge bar (`JUDGE.md`): never-kill intact for the two items this lane can touch. **Redaction** — the raw prompt never leaves the process: `Span.finish` emits `prompt_hash` (sha256) plus a masked `prompt_preview` (`[EMAIL]` / `[SSN]`, ≤200 chars) and only when `sensitive=True`, drops its prompt reference on close, and `tests/test_no_raw_log.py` asserts the email and SSN appear in neither stdout, logs, nor the preview. The offline `.last-flight.json` holds the same masked spans and is gitignored, so nothing raw reaches git either. This preview is a **hint**, not the authority — Alexis's ingest redaction stays the fail-closed gate. **Ingest key ≠ user JWT** — the client sends `X-Tenant-Key` (`TRACEVAULT_TENANT_KEY`) and nothing else; there is no `Authorization` header and no Cognito code path in `sdk/`. The other never-kills (403 not 404, HTTPS URL, fixture UI, `/health`, CORS, JWT `custom:tenant_id`, one retrieve tool) have no surface in this PR.

## What I shipped

- files: `sdk/pyproject.toml`, `sdk/README.md`, `sdk/src/tracevault/{__init__,client,span,context,schema,redact_hint}.py`, `sdk/tests/{test_golden_span,test_nesting,test_no_raw_log}.py`, `sdk/tests/golden/root_span.json`, `sdk/.gitignore`, `sdk/.bandit`, `sdk/uv.lock`
- outputs / env **names** (no secret values): `TRACEVAULT_INGEST_URL`, `TRACEVAULT_TENANT_KEY`, `TRACEVAULT_TENANT_ID`
- tests: `uv run pytest` in `sdk/` — 3 passed

## What I need

- from whom: Alexis (ingest `POST /v1/traces` + `X-Tenant-Key`); Trevor-ci (`sdk.yml` to run these tests)
- contract / URL / header / path: `POST {TRACEVAULT_INGEST_URL}/v1/traces` JSON `{"spans":[...]}` header `X-Tenant-Key`; schema `contracts/span.schema.json` when hour 0 lands (SDK embeds draft fallback)

## Blocked on

Alexis ingest live URL. Hour 0 `contracts/span.schema.json` (validates draft/embed until then). `trevor-ci` `sdk.yml`.

## Contract reminder

SDK **emits** schema-shaped spans and POSTs the batch. Alexis redacts at ingest. SDK is not Presidio and does not persist the vault. Raw prompts are never logged.