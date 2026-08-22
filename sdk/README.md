# tracevault

Python client that **emits** TraceVault spans. One request = one flight = one `trace_id` with child spans (`llm`, `tool`, `rag`, `http`). This package is not the vault and not the Explorer UI.

## Install

```bash
cd sdk
uv sync --extra dev
```

## Usage

```python
from tracevault import TraceVaultClient, start_span

client = TraceVaultClient.from_env()
with start_span(client, kind="llm", name="chat", model="...", sensitive=True, prompt=user_text):
    ...
client.flush()
```

## Environment

| Name | Required | Default |
|---|---|---|
| `TRACEVAULT_INGEST_URL` | no | unset → write `sdk/.last-flight.json`, do not crash |
| `TRACEVAULT_TENANT_KEY` | with ingest URL | — |
| `TRACEVAULT_TENANT_ID` | no | `tenant-a` |

Do not put secret values in this file or in git.

`POST {TRACEVAULT_INGEST_URL}/v1/traces` JSON `{"spans":[...]}` header `X-Tenant-Key`. Timeout 5s.

## Tests

```bash
cd sdk
uv run pytest
```

No Bedrock calls in unit tests. Raw prompts are never printed or logged.
