# demo-app

Instrumented RAG/agent that emits **one TraceVault flight**. Not a product. Judges never use this except via `scripts/demo_pii_flight.sh` (trevor-scripts). **One tool only:** `get_doc_metadata` (retrieve). No write, delete, or shell tools.

## Fake Bedrock (P-15)

If `TRACEVAULT_FAKE_BEDROCK=1`, embeddings and `converse` are **stubs**. No AWS network. Tests use this path. Say so if a judge demo is run with the flag set — that is not live Bedrock.

Live path (flag unset): Amazon Bedrock in `AWS_REGION` (default `us-east-1`), model ids from env.

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
| `BEDROCK_MODEL_ID` | Converse model (required unless fake) |
| `BEDROCK_EMBED_MODEL_ID` | Embeddings model (required unless fake) |
| `TRACEVAULT_INGEST_URL` | Ingest base URL. Unset → write `.last-flight.json`, do not crash |
| `TRACEVAULT_TENANT_KEY` | Ingest `X-Tenant-Key` |
| `TRACEVAULT_TENANT_ID` | Default tenant if not passed as `--tenant` |
| `TRACEVAULT_FAKE_BEDROCK` | `1` = stub embedder + converse (P-15) |

`--tenant` is `tenant-a` or `tenant-b`.

## Spans

`http` `demo.ask` (root) → `rag` `demo.retrieve`, `tool` `demo.get_doc_metadata`, `llm` `demo.converse`. One `trace_id`. Fake llm usage is tokens `1`/`1`, cost `0`.

## SDK

`pyproject.toml` comments the optional path dep on `../sdk` so this branch installs without #28. After that PR merges, uncomment `[tool.uv.sources]` + extra `sdk` and `uv sync --extra sdk`. Until then, emit goes through a `DemoEmitter` protocol stub so fake-bedrock tests pass without importing `tracevault`.
