# AI usage

**What this is:** the honest record of which AI tools each human on Team Summer.exe used while building TraceVault, what those tools helped with, and how a human still owned the result. It also names the model the **product itself** calls at runtime.

**Handbook item:** P-06 (AI transparency). It is also the evidence behind the rubric row *Team & AI-tool (5)* — feature PRs, committed handoffs, a human merge, and this file.

**How to read this file:** humans did the planning, architecture, threat model, lane splits, and ship/no-ship decisions. AI tools (Cursor, Claude Code, Codex) were used to troubleshoot, surface bugs, draft boilerplate, and speed up implementation under that human direction — not as autonomous authors of the product. Every disclosed tool below is real; nothing here invents a model or workflow we did not use.

## How humans used AI

| Human | Tool / model | What AI helped with | Human ownership / review |
|---|---|---|---|
| Trevor | Claude Code / Cursor (Claude-based assistants), often one focused session per lane (`trevor-contracts`, `trevor-sdk`, `trevor-demo`, `trevor-scripts`, `trevor-infra`, `trevor-ci`, `trevor-docs`) | Boilerplate and first drafts in `contracts/`, `sdk/`, `demo-app/`, `scripts/`, `infra/`, `.github/`, `Makefile`, and submission docs; grepping for regressions; suggesting fixes during CI/infra troubleshooting | Trevor designed the lane map, contracts, IAM/OIDC shape, and merge policy. Diffs land only via feature-branch PRs with a committed `handoffs/` file; Trevor reads each diff and merges to `main` himself. `main` is protected — assistants cannot push or merge. |
| Alexis | Claude Code (Claude Fable 5), often one focused session per mission (`alexis-redact`, `alexis-ingest`, `alexis-audit`, `alexis-read`, `alexis-redteam`) | Drafting and iterating vault code/tests under human direction — `redact/`, `store/`, `ingest/` + `handlers/ingest.py`, `read/` + `handlers/read.py`, `audit/`, `errors.py`, plus abuse/red-team docs and harness scaffolding | Alexis owned fail-closed redaction design, ingest/read/audit behaviour, and the live AWS verification plan. Each mission used a branch + `handoffs/alexis-*.md` PR; Trevor merges. Alexis ran `pytest` + `bandit`, secret-scanned diffs before push, reviewed the cross-lane `vault/audit` fix (#72), and confirmed live ingest/read/403/audit plus raw S3/Dynamo contents (`docs/RED_TEAM.md`). |
| Michael | OpenAI Codex (GPT-5) in the shared workspace, plus local shell and GitHub CLI for issue/PR checks | Speeding up explorer UI scaffolding, fixture/live wiring drafts, operator-state polish, Playwright stubs, and doc edits in `web/`, `PRODUCT.md`, `DESIGN.md`, and Michael handoffs | Michael matched work to live GitHub issue text, chose UX/operator-state behaviour, and verified with ESLint, `next build`, and Playwright before asking for merge. Trevor still performs the human PR merge review; nothing lands on `main` directly from an assistant. |

Verifiable from this repo without taking anyone's word for it: feature work still goes through a matching `handoffs/<name>-<id>-<slug>.md` on the branch (and as the PR body). That process is how we keep parallel lanes honest — it is **not** a claim that assistants designed the system. `git log --merges` and `handoffs/` are the review record, including Michael's explorer handoffs for the fixture and live follow-up PRs.

> **This file is the *tool* disclosure — which AI tools the humans used.** It is not the model inventory. What the **product** depends on at runtime — model ids, versions, inference settings, the RAG corpus as a dataset, and every external service the AI path touches — is [`docs/AI_INVENTORY.md`](docs/AI_INVENTORY.md). The two are kept apart on purpose: conflating "we used Claude Code while writing this" with "the product calls Bedrock" is exactly the ambiguity the handbook's *unknown dependencies* red flag is looking for. The section below is the short version; the inventory is authoritative.

## Model used by the product itself

| Field | Value |
|---|---|
| Provider | Amazon Bedrock |
| Model family | Claude **or** Nova (whichever is enabled on the account) |
| Region | `us-east-1` |
| Permitted model ids | `anthropic.claude-3-5-sonnet-20241022-v2:0`, `amazon.nova-lite-v1:0` — both allowed simultaneously so the second is a fallback |
| Exact deployed id | Default live converse model: `amazon.nova-lite-v1:0`. Override with `BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0`. Both are on the IAM allowlist after apply. |
| Embedding model | `amazon.titan-embed-text-v2:0` (pinned in `bedrock_model_ids` and `DEFAULT_EMBED_MODEL_ID`) |
| Where the id is configured | `infra/envs/*.tfvars` (`bedrock_model_ids`) and `BEDROCK_MODEL_ID` / `BEDROCK_EMBED_MODEL_ID` in `demo-app/` (defaults to Nova Lite + Titan Embed V2). Never hardcoded secrets — only model ids. |
| Key inference settings | `maxTokens` 256, `temperature` 0, one attempt (no retries), 30 s read timeout |
| What it is used for | One LLM answer per demo flight, over a small local corpus retrieved by a single read-only RAG tool |
| Faking it | `TRACEVAULT_FAKE_BEDROCK=1` makes the demo return a canned response instead of calling Bedrock. **Every test in this repo runs this way.** If the demo is run that way, say so out loud — see **Demo integrity (P-15)** in the README |
| IAM scope | `bedrock:InvokeModel` limited to the model ARNs generated from tfvars. No wildcard model access |

The model sees only the demo prompt and the retrieved corpus text. Model output is stored the same way a prompt is — redacted at ingest, hashed and masked, TTL 7 days. That ingest path is **implemented and tested** (`vault/`, 83 tests); the read path is not, and nothing has been deployed. See **Demo integrity (P-15)** in the README for the built-versus-deployed split, and [`GOVERNANCE.md`](GOVERNANCE.md) for who owns what when it fails.

## Not used

- **No mystery Copilot commits.** AI-assisted changes still arrive as feature-branch PRs with a committed handoff and a named session/agent id. There are no unattributed drive-by commits on `main`.
- **No autonomous infrastructure changes.** No assistant holds AWS credentials, runs `terraform apply`, or deploys. Deployment happens only from `main` via `deploy.yml` with GitHub OIDC, after Trevor merges. Rollback is a human re-running the last green `deploy.yml`.
- **No assistant merges its own work.** Only Trevor merges. `contracts/` changes additionally need all three humans on the thread.
- **No AI in the request path beyond the demo.** TraceVault does not use an LLM to triage, summarise, or auto-remediate traces. Humans read the traces. There is no RCA-via-Bedrock feature.
- **No write-capable agent tools in the product.** The demo agent has exactly one retrieve tool on an allowlist — no write, no delete, no shell.
- **No real customer data.** Demo PII is synthetic.
