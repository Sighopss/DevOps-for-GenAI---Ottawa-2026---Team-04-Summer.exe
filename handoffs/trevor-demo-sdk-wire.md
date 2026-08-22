# Handoff — demo uses the real TraceVault SDK (#35)

- Date: 2026-08-22
- Human/owner: Trevor
- Branch: `trevor/demo/sdk-wire` from `origin/main` at `6e41c7d`
- Issue: closes #35 after merge

## Claimed paths

```text
demo-app/src/demo_app/emitter.py
demo-app/pyproject.toml
demo-app/uv.lock
demo-app/tests/test_span_graph.py
handoffs/trevor-demo-sdk-wire.md
```

Collision check: PR #89 touches other named `demo-app` files (`README.md`, `bedrock.py`, `main.py`, `rag.py`, and `test_agent_controls.py`) but none of the paths above. PR #88 is Michael's `web/`; #76 and #78 are docs/CODEOWNERS. No overlap.

## What changed

- `demo-app` now has a real editable path dependency on `../sdk` through `tool.uv.sources`.
- `load_emitter()` imports and returns `tracevault.TraceVaultClient` and `tracevault.start_span` directly.
- The duplicated `DemoEmitter`, `StubClient`, `StubSpan`, and `stub_start_span` implementation is gone; there is no fallback branch that can silently avoid the SDK.
- When `TRACEVAULT_INGEST_URL` is unset, fallback behavior comes from the SDK itself and writes `sdk/.last-flight.json`, preserving the frozen contract.
- The test asserts the default emitter's concrete type is `TraceVaultClient`.
- Existing fake-Bedrock tests still prove four spans and prove synthetic email/SSN never reach logs or an unmasked preview.

## Handbook evidence

| Gate | Evidence |
|---|---|
| Build / Engineering | Demo and recorder use one implementation rather than a forked span emitter |
| Validate / Sensitive data | `--pii` test remains green through the real SDK redaction hint path |
| Resilience | Unset ingest URL exercises the SDK's documented local fallback |
| P-15 | `TRACEVAULT_FAKE_BEDROCK=1` remains explicit; this change does not claim a live Bedrock call |
| Supply chain | Local SDK dependency and its transitive packages are captured in `demo-app/uv.lock` |

## Validation

```text
cd demo-app
uv lock
uv sync --frozen --extra dev
TRACEVAULT_FAKE_BEDROCK=1 uv run pytest -q
  3 passed
```

The boto3 client is replaced with a trap in tests, so this validation makes no AWS call. No infrastructure was applied.

## Known documentation follow-up

`demo-app/README.md` still contains the pre-#28 SDK TODO. It is currently claimed by open PR #89, so this PR deliberately does not collide with that file. Remove the stale paragraph after the two PRs are ordered/merged.
