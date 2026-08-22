# Handoff — trevor-demo-cost-usd — cost_usd on the live Bedrock path

- Date: 2026-08-22
- Human: Trevor
- Agent id: trevor-demo-cost-usd
- Branch: `trevor/118/demo-cost-usd`
- PR: TBD
- Mission / scope: issue #118 — compute real `cost_usd` on the live Bedrock `converse` path instead of the hardcoded `0.0`.

## Claimed paths (collision)

```
demo-app/src/demo_app/pricing.py   (new)
demo-app/src/demo_app/bedrock.py
demo-app/src/demo_app/main.py
demo-app/tests/test_pricing.py     (new)
demo-app/tests/test_agent_controls.py
sdk/src/tracevault/span.py
sdk/tests/test_usage_cost.py       (new)
handoffs/trevor-demo-cost-usd.md
```

## Do not touch

```
vault/
infra/
.github/
docs/
web/
contracts/
README.md
SECURITY.md
```

## Safe to run in parallel with

Any agent not writing under `demo-app/` or `sdk/`. No open PRs claimed either path at the time this branch was cut (`gh pr list --state open` was empty).

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Build` / `Validate`
- P-ids this PR moves: P-15 (honest live vs stub — `cost_usd` no longer pretends a live call is free), inventory closure noted in `docs/AI_INVENTORY.md`'s "Recorded gaps" line (that doc is out of my path fence — flagging for whoever owns `docs/` to strike that line once this merges)
- Tests / attack shown: `demo-app/tests/test_pricing.py` (8 tests: known-model math, cross-model ordering, Decimal round-trip cleanliness, zero-token edge case, negative-token rejection, unknown-model fallback is loud not silent, embed model has no output rate, allowlisted models all have a rate). `demo-app/tests/test_agent_controls.py` gained two tests: live `converse()` with a mocked Bedrock client returning realistic usage now asserts `cost_usd > 0.0`, and fake mode still asserts `cost_usd == 0.0` with a note explaining it's a stub. `sdk/tests/test_usage_cost.py` (3 tests) covers the new `Span.set_usage(attributes=...)` merge behavior. All existing suites still pass unmodified in intent.
- Stub/live (P-15): `TRACEVAULT_FAKE_BEDROCK=1` is unchanged — `cost_usd` stays `0.0` there **by definition** (it's not a live call, there's nothing to price), and `ConverseResult.cost_note` now says so explicitly (`"TRACEVAULT_FAKE_BEDROCK=1: stub, not a live call, cost_usd is definitionally 0.0"`). The live path computes `cost_usd` from real `usage.inputTokens`/`usage.outputTokens` on the Bedrock `Converse` response times a per-model rate table.
- Judge bar (`JUDGE.md`): never-kill intact. Nothing on the never-kill list touched. Metric 2 ("waterfall + hops + tokens + `$`") is what this PR fixes — a live flight's `llm` span can now show a non-zero `$` instead of `0.0`.

## What I shipped

### The gap (confirmed by reading code, not assumed)

- `demo_app/bedrock.py::converse()` already read real `usage.inputTokens` / `usage.outputTokens` off the live Bedrock `Converse` response (`response.get("usage")`) — tokens were never the problem.
- `cost_usd` was hardcoded `cost_usd=0.0` on the live branch, unconditionally, regardless of tokens or model.
- Fake mode (`TRACEVAULT_FAKE_BEDROCK=1`) already emitted `FAKE_COST_USD = 0.0` too, but that's correct for a stub — the bug was that live had the exact same number for a different reason (nothing computed it), and nothing distinguished the two paths' zeros.
- `sdk/src/tracevault/span.py::Span.set_usage()` already threaded `cost_usd` through to the span payload and `contracts/span.schema.json` already had `cost_usd: {type: number, minimum: 0}` — the contract needed no change.

### The fix

- **New `demo_app/pricing.py`.** A frozen `RATE_TABLE: dict[str, ModelRate]` (`Decimal` input/output USD-per-1K-tokens), one entry per model id, with a source comment citing where the numbers came from and when. `estimate_cost_usd(model_id, *, input_tokens, output_tokens) -> CostEstimate` does the arithmetic in `Decimal` and quantizes to 8 decimal places before converting to `float`, so `Decimal(str(cost_usd))` (what `vault/store/keys.py` does when writing DynamoDB) round-trips cleanly instead of picking up binary-float noise.
- **Unknown-model fallback is loud, not silent.** If `model_id` has no rate-table entry, `estimate_cost_usd` logs at `ERROR` (`demo_app.pricing` logger) and returns `CostEstimate(usd=0.0, known=False, note="cost_usd estimate-unavailable: ...")` — the `0.0` is never returned without the `known=False` flag and an explanatory note attached, satisfying the issue's "or explicitly labels the field as estimate-unavailable" acceptance criterion. In practice this path is defense-in-depth: every id in `bedrock.ALLOWED_CONVERSE_MODEL_IDS` plus the embed model id has a rate-table entry today (asserted by a test), so it only fires if a future PR adds a model to the allowlist without adding a price.
- **`bedrock.converse()`** now calls `estimate_cost_usd(model, input_tokens=..., output_tokens=...)` on the live branch and returns the result on a widened `ConverseResult` (`cost_known: bool`, `cost_note: str` added, both defaulted so nothing else calling the dataclass breaks). Fake mode gets its own constant note explaining it's a disclosed stub.
- **`sdk/src/tracevault/span.py`**: `Span.set_usage()` gained an optional `attributes: dict[str, Any] | None` kwarg that merges into the span's existing `attributes` dict (doesn't clobber attributes set at span-open time). `demo_app/main.py` uses it to attach `cost.known` / `cost.note` onto the `llm` span's `attributes` — visible in the Explorer/logs without touching the frozen `contracts/span.schema.json` (that schema already allows arbitrary keys under `attributes`).

### Worked example

Nova Lite (`amazon.nova-lite-v1:0`, the default converse model and the one that's actually invokable today per `docs/AI_INVENTORY.md` — Claude 3.5 Sonnet v2 is EOL/`ResourceNotFoundException` on Bedrock right now), a realistic single-turn RAG answer against the demo's 3-document corpus:

```
input_tokens  = 612
output_tokens = 143
rate          = $0.00006 / 1K input tokens, $0.00024 / 1K output tokens

cost = (612 / 1000 * 0.00006) + (143 / 1000 * 0.00024)
     = 0.00003672 + 0.00003432
     = 0.00007104   ->  cost_usd = 7.104e-05  (== $0.00007104)
```

Same tokens against Claude 3.5 Sonnet v2's rate ($0.006 / $0.03 per 1K, its current Bedrock "Public Extended Access" EOL pricing) would be `$0.007962` — over 100x Nova Lite's cost for the same call, which is the right ordering and is asserted by a test.

### Where the pricing figures came from — point-in-time, not authoritative

Captured 2026-08-22 from the public AWS Bedrock pricing page (`https://aws.amazon.com/bedrock/pricing/`), on-demand, `us-east-1` (the demo's fixed `AWS_REGION` default):

| Model | Input $/1K tok | Output $/1K tok | Note |
|---|---|---|---|
| `anthropic.claude-3-5-sonnet-20241022-v2:0` | $0.006 | $0.03 | Billed under AWS's "Public Extended Access" schedule (effective 2025-12-01) because the model is EOL on Bedrock — this is what a live call would actually bill today, not the original GA rate |
| `amazon.nova-lite-v1:0` | $0.00006 | $0.00024 | Published on-demand rate |
| `amazon.titan-embed-text-v2:0` | $0.00002 | $0 (embeddings have no output tokens) | Published on-demand rate |

**These are not a substitute for AWS Cost Explorer / real billing** (explicitly out of scope on #118) and AWS revises Bedrock pricing without notice — re-check the page above before trusting these numbers for anything beyond this hackathon demo. The source URL and capture date are recorded in `demo_app/pricing.py`'s module docstring and repeated in every `CostEstimate.note`/log line, so a stale number is traceable, not silently wrong.

- outputs / env **names** (no secret values): none new — `RATE_TABLE_AS_OF` / `RATE_SOURCE` are code constants, not env vars.
- tests: `cd demo-app && TRACEVAULT_FAKE_BEDROCK=1 uv run pytest` (20 passed) and `cd sdk && uv run pytest` (6 passed). `uv run bandit -r src` (sdk) — no issues.

## What I need

- from whom: nobody — this PR is self-contained within `demo-app/` and `sdk/`.
- contract / URL / header / path: none changed. `contracts/span.schema.json` and `contracts/http.md` were read, not edited — `cost_usd: number, minimum 0` already covers this.

## Blocked on

Nobody. One follow-up I can't do myself because it's outside my path fence: `docs/AI_INVENTORY.md`'s "Recorded gaps" line currently reads *"the live converse path hardcodes `cost_usd = 0.0`"* — that's now false and should be struck by whoever owns `docs/`.

## Contract reminder

`cost_usd` on the `llm` span: a non-negative `float`, estimated from real Bedrock `usage` tokens × a documented per-model rate table, quantized for clean `Decimal` storage. Not real AWS billing — a same-order-of-magnitude estimate for the demo/judge path.
