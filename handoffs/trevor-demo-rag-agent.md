# Handoff — trevor-demo — rag-agent

- Date: 2026-08-21
- Human: Trevor
- Agent id: trevor-demo
- Branch: trevor/demo/rag-agent
- PR: TBD
- Mission file: `skills/trevor-recorder/agents/demo.md`

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
demo-app/
handoffs/trevor-demo-rag-agent.md
```

## Do not touch

```
sdk/
scripts/
vault/
web/
infra/
.github/
Makefile
contracts/
PRODUCT.md
DESIGN.md
assets/
```

## Safe to run in parallel with

`trevor-sdk` (#28), `trevor-ci` (#27), `trevor-infra` (#29), `trevor-contracts` (#26), `trevor-scripts` (once this CLI exists), Alexis vault, Michael web. Not with another `trevor-demo` writer.

## Handbook evidence (required — 2026 workbook)

Empty = incomplete PR. Copy from PLAN **Rubric 100** / P-ids.

- Lifecycle stage: `Build`
- P-ids this PR moves: `P-09`, `P-15`
- Rubric rows (pts): `Engineering 15`
- Tests / attack shown: `test_span_graph.py` with `TRACEVAULT_FAKE_BEDROCK=1` — 4 spans, one `trace_id`, `parent_id` graph (`http` root → `rag`/`tool`/`llm`). boto3 client patched to fail (no AWS network). `--pii` marks llm `sensitive=True`; email/SSN never appear in logs/stdout/`prompt_preview`. One retrieve tool only (`get_doc_metadata`).
- Stub/live (P-15): Tests and README use **stub** Bedrock when `TRACEVAULT_FAKE_BEDROCK=1`. Live Bedrock `converse` + embeddings when the flag is unset (`AWS_REGION`, `BEDROCK_MODEL_ID`, `BEDROCK_EMBED_MODEL_ID`). SDK ingest is live POST when `TRACEVAULT_INGEST_URL` is set; otherwise `.last-flight.json`. `tracevault` import is stubbed behind `DemoEmitter` until #28 merges.
- Judge bar (`JUDGE.md`): never-kill intact. **One retrieve tool** — `demo_app/rag.py` exposes exactly one allowlisted tool, `get_doc_metadata`, read-only over `demo-app/corpus/*.md`, confined with `is_relative_to(root)` and failing closed (`KeyError`) on an unknown id. No write, delete, shell, or network tool exists in the tree, and `main.py` opens exactly one `kind="tool"` span. **Redaction** — `--pii` prepends the synthetic email/SSN and marks only the `llm` span `sensitive=True`; the emitter records `prompt_hash` + `[EMAIL]` / `[SSN]` preview, never the raw text, the CLI logs only `running with --pii (prompt not logged)`, and `test_pii_marks_llm_without_logging_prompt` asserts neither value reaches logs, stdout, or preview. `.last-flight.json` is gitignored. Fake Bedrock is disclosed in the P-15 row above. Honest caveat, not a break: the CLI prints the model's **answer**, which that test does not cover under live Bedrock — a live model could restate what it was given. Nothing stored or ingested is affected; flagging it for Trevor.

## What I shipped

- files:
  - `demo-app/pyproject.toml` (path dep `../sdk` commented until #28 merges; `DemoEmitter` stub runs tests now)
  - `demo-app/README.md` (documents `TRACEVAULT_FAKE_BEDROCK=1` and `--pii`)
  - `demo-app/src/demo_app/{__init__,main,rag,bedrock,emitter}.py`
  - `demo-app/corpus/{01-overview,02-retention,03-tenancy}.md`
  - `demo-app/tests/test_span_graph.py`
  - `demo-app/uv.lock`
  - `handoffs/trevor-demo-rag-agent.md`
- outputs / env **names** (no secret values):
  - `AWS_REGION`
  - `BEDROCK_MODEL_ID`
  - `BEDROCK_EMBED_MODEL_ID`
  - `TRACEVAULT_INGEST_URL`
  - `TRACEVAULT_TENANT_KEY`
  - `TRACEVAULT_TENANT_ID`
  - `TRACEVAULT_FAKE_BEDROCK`
- tests: `TRACEVAULT_FAKE_BEDROCK=1 uv run pytest` in `demo-app/` — span graph + no-PII-log

## What I need

- from whom: trevor-sdk (#28) so `import tracevault` works from `../sdk`; trevor-scripts for `scripts/demo_pii_flight.sh`; Alexis for live `POST /v1/traces`; Human Trevor merges #28 before live ingest from this CLI.
- contract / URL / header / path: `POST {TRACEVAULT_INGEST_URL}/v1/traces` JSON `{"spans":[...]}` header `X-Tenant-Key`. CLI: `uv run python -m demo_app.main --question "..." --tenant tenant-a [--pii]`

## Blocked on

`trevor-sdk` (#28) for the real client (this PR stubs `DemoEmitter` so tests pass now). `trevor-scripts` for the judge script. Alexis ingest URL for live POST.

## Contract reminder

Demo is not a product. One retrieve tool (`get_doc_metadata`). No write/delete/shell. `--pii` prepends synthetic email/SSN and sets llm `sensitive=True`; never log that prompt. Fake Bedrock must be disclosed (P-15). Ingest is `X-Tenant-Key`, not Cognito.