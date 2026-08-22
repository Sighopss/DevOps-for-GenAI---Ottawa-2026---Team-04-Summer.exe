# AI usage

**What this is:** the honest record of which AI tools each human on Team Summer.exe used to build TraceVault, what those tools produced, and how a human reviewed it. It also names the model the **product itself** calls at runtime.

**Handbook item:** P-06 (AI transparency). It is also the evidence behind the rubric row *Team & AI-tool (5)* — feature PRs, committed handoffs, a human merge, and this file.

> **Action required before submission (D2 PM):** Alexis and Michael each append **their own rows** below. Do not let another person write your row — the point of this file is that the human who used the tool says what they used it for. Rows pre-seeded by Trevor cover only Trevor's lane.

## How humans used AI

| Human | Tool / model | What it produced | Human review |
|---|---|---|---|
| Trevor | Claude-based coding agents (Claude Code / Cursor), one agent per lane: `trevor-contracts`, `trevor-sdk`, `trevor-demo`, `trevor-scripts`, `trevor-infra`, `trevor-ci`, `trevor-docs` | `contracts/`, `sdk/`, `demo-app/`, `scripts/`, `infra/`, `.github/`, `Makefile`, and this submission shell (`README.md`, `AI_USAGE.md`, `handoffs/`) | Every agent worked on its own branch and opened a PR. Each PR commits a handoff file under `handoffs/` naming claimed paths, handbook evidence, and stub/live status; the same text is the PR body. No agent merges — Trevor reads the diff and merges to `main` himself. `main` is protected; agents cannot push to it. |
| Alexis | _append: tool + model_ | _append: what it produced (`vault/` redact / store / ingest / read / audit / tests)_ | _append: how you reviewed it_ |
| Michael | OpenAI Codex coding agent (GPT-5) in the shared workspace, plus local shell tools and GitHub CLI reads for issue/PR verification | `web/` explorer routes, fixture/live read wiring, tenant/403 chrome, operator-state UI polish, Playwright coverage, `PRODUCT.md`, `DESIGN.md`, and Michael handoff updates | Michael's lane work was matched against the live GitHub issue text before coding, then verified locally with ESLint, `next build`, and Playwright. Trevor still performs the human PR merge review; nothing lands on `main` directly from the agent. |

Verifiable from this repo without taking anyone's word for it: every feature branch carries a matching `handoffs/<name>-<id>-<slug>.md`, committed on that branch and repeated as the PR body. If a change has no handoff, it did not go through this process. `git log --merges` and the files under `handoffs/` are the record, including Michael's explorer handoffs for the fixture and live follow-up PRs.

> **This file is the *tool* disclosure — which AI tools the humans used.** It is not the model inventory. What the **product** depends on at runtime — model ids, versions, inference settings, the RAG corpus as a dataset, and every external service the AI path touches — is [`docs/AI_INVENTORY.md`](docs/AI_INVENTORY.md). The two are kept apart on purpose: conflating "we used Claude Code to write this" with "the product calls Bedrock" is exactly the ambiguity the handbook's *unknown dependencies* red flag is looking for. The section below is the short version; the inventory is authoritative.

## Model used by the product itself

| Field | Value |
|---|---|
| Provider | Amazon Bedrock |
| Model family | Claude **or** Nova (whichever is enabled on the account) |
| Region | `us-east-1` |
| Permitted model ids | `anthropic.claude-3-5-sonnet-20241022-v2:0`, `amazon.nova-lite-v1:0` — both allowed simultaneously so the second is a fallback |
| Exact deployed id | **TBD** — nothing is deployed, so no id has been *used* yet. Recorded here once an apply fixes it |
| Embedding model | `BEDROCK_EMBED_MODEL_ID` — **not yet pinned, and not yet in the IAM allowlist.** See the gap recorded in [`docs/AI_INVENTORY.md`](docs/AI_INVENTORY.md) |
| Where the id is configured | `infra/envs/*.tfvars` (`bedrock_model_ids`) and the `BEDROCK_MODEL_ID` environment variable read by `demo-app/`. Never hardcoded in application code |
| Key inference settings | `maxTokens` 256, `temperature` 0, one attempt (no retries), 30 s read timeout |
| What it is used for | One LLM answer per demo flight, over a small local corpus retrieved by a single read-only RAG tool |
| Faking it | `TRACEVAULT_FAKE_BEDROCK=1` makes the demo return a canned response instead of calling Bedrock. **Every test in this repo runs this way.** If the demo is run that way, say so out loud — see **Demo integrity (P-15)** in the README |
| IAM scope | `bedrock:InvokeModel` limited to the model ARNs generated from tfvars. No wildcard model access |

The model sees only the demo prompt and the retrieved corpus text. Model output is stored the same way a prompt is — redacted at ingest, hashed and masked, TTL 7 days. That ingest path is **implemented and tested** (`vault/`, 83 tests); the read path is not, and nothing has been deployed. See **Demo integrity (P-15)** in the README for the built-versus-deployed split, and [`GOVERNANCE.md`](GOVERNANCE.md) for who owns what when it fails.

## Not used

- **No mystery Copilot commits.** Every AI-authored change arrives as a feature-branch PR with a committed handoff and a named agent id. There are no unattributed commits on `main`.
- **No autonomous infrastructure changes.** No agent holds AWS credentials, runs `terraform apply`, or deploys. Deployment happens only from `main` via `deploy.yml` with GitHub OIDC, after Trevor merges. Rollback is a human re-running the last green `deploy.yml`.
- **No agent merges its own work.** Only Trevor merges. `contracts/` changes additionally need all three humans on the thread.
- **No AI in the request path beyond the demo.** TraceVault does not use an LLM to triage, summarise, or auto-remediate traces. Humans read the traces. There is no RCA-via-Bedrock feature.
- **No write-capable agent tools in the product.** The demo agent has exactly one retrieve tool on an allowlist — no write, no delete, no shell.
- **No real customer data.** Demo PII is synthetic.
