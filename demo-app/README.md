# demo-app

Instrumented RAG/agent that emits **one TraceVault flight**. Not a product. Judges never use this except via `scripts/demo_pii_flight.sh` (trevor-scripts). **One tool only:** `get_doc_metadata` (retrieve). No write, delete, or shell tools.

## Agent/tool security evidence

The callable registry is immutable and contains exactly `get_doc_metadata`. The tool returns metadata only, rejects paths that resolve outside `demo-app/corpus/`, and has no write, delete, shell, or network capability. The workflow has no agent loop: one flight makes exactly one Converse call, capped at 256 output tokens, a 5-second connect timeout, a 30-second read timeout, and one retry. `tests/test_agent_controls.py` makes these properties fail CI if they drift. See [`../docs/SCALE.md`](../docs/SCALE.md) for the 10× and limit-behavior evidence.

Live path (flag unset): Amazon Bedrock in `AWS_REGION` (default `us-east-1`). Agreed models:

| Role | Default id | Allowlisted alternate |
|---|---|---|
| Converse | `amazon.nova-lite-v1:0` | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| Embeddings | `amazon.titan-embed-text-v2:0` | — |

Override with `BEDROCK_MODEL_ID` / `BEDROCK_EMBED_MODEL_ID`. Any converse id outside the allowlist fails closed.

## Fake Bedrock (P-15)

If `TRACEVAULT_FAKE_BEDROCK=1`, embeddings and `converse` are **stubs**. No AWS network. Tests use this path. Say so if a judge demo is run with the flag set — that is not live Bedrock.

## Run

```bash
cd demo-app
uv sync --extra dev
uv run pytest

TRACEVAULT_FAKE_BEDROCK=1 uv run python -m demo_app.main \
  --question "What is the retention TTL?" \
  --tenant tenant-a
```

`--pii` prepends `Contact user@example.com SSN 123-45-6789. ` and marks the llm span `sensitive=True`. The prompt is **never logged**.

```bash
TRACEVAULT_FAKE_BEDROCK=1 uv run python -m demo_app.main \
  --question "What is the retention TTL?" \
  --tenant tenant-a \
  --pii
```

## Environment (names only — no secret values)

| Name | Role |
|---|---|
| `AWS_REGION` | Bedrock region, default `us-east-1` |
| `BEDROCK_MODEL_ID` | Converse model (default Nova Lite; Claude also allowlisted) |
| `BEDROCK_EMBED_MODEL_ID` | Embeddings model (default Titan Embed V2) |
| `TRACEVAULT_INGEST_URL` | Ingest base URL. Unset → write `.last-flight.json`, do not crash |
| `TRACEVAULT_TENANT_KEY` | Ingest `X-Tenant-Key` |
| `TRACEVAULT_TENANT_ID` | Default tenant if not passed as `--tenant` |
| `TRACEVAULT_FAKE_BEDROCK` | `1` = stub embedder + converse (P-15) |

`--tenant` is `tenant-a` or `tenant-b`.

## Spans

`http` `demo.ask` (root) → `rag` `demo.retrieve`, `tool` `demo.get_doc_metadata`, `llm` `demo.converse`. One `trace_id`. Fake llm usage is tokens `1`/`1`, cost `0`.

## SDK

`pyproject.toml` comments the optional path dep on `../sdk` so this branch installs without #28. After that PR merges, uncomment `[tool.uv.sources]` + extra `sdk` and `uv sync --extra sdk`. Until then, emit goes through a `DemoEmitter` protocol stub so fake-bedrock tests pass without importing `tracevault`.
