# AI usage

**What this is:** the honest record of which AI tools each human on Team Summer.exe used to build TraceVault, what those tools produced, and how a human reviewed it. It also names the model the **product itself** calls at runtime.

**Handbook item:** P-06 (AI transparency). It is also the evidence behind the rubric row *Team & AI-tool (5)* — feature PRs, committed handoffs, a human merge, and this file. The scoring text itself stays in the scratchbook (`PLAN.md` / `JUDGE.md` at https://github.com/Sighopss/TVault-scratchbook-accessible); this file is product-repo evidence only.

> **Action required before submission (D2 PM):** Alexis and Michael each append **their own rows** below. Do not let another person write your row — the point of this file is that the human who used the tool says what they used it for. Rows pre-seeded by Trevor cover only Trevor's lane.

## How humans used AI

| Human | Tool / model | What it produced | Human review |
|---|---|---|---|
| Trevor | Claude-based coding agents (Claude Code / Cursor), one agent per lane: `trevor-contracts`, `trevor-sdk`, `trevor-demo`, `trevor-scripts`, `trevor-infra`, `trevor-ci`, `trevor-docs` | `contracts/`, `sdk/`, `demo-app/`, `scripts/`, `infra/`, `.github/`, `Makefile`, and this submission shell (`README.md`, `AI_USAGE.md`, `handoffs/`) | Every agent worked on its own branch and opened a PR. Each PR commits a handoff file under `handoffs/` naming claimed paths, handbook evidence, and stub/live status; the same text is the PR body. No agent merges — Trevor reads the diff and merges to `main` himself. `main` is protected; agents cannot push to it. |
| Alexis | _append: tool + model_ | _append: what it produced (`vault/` redact / store / ingest / read / audit / tests)_ | _append: how you reviewed it_ |
| Michael | _append: tool + model_ | _append: what it produced (`web/`, `PRODUCT.md`, `DESIGN.md`, Playwright)_ | _append: how you reviewed it_ |

Verifiable from this repo without taking anyone's word for it: every feature branch carries a matching `handoffs/<name>-<id>-<slug>.md`, committed on that branch and repeated as the PR body. If a change has no handoff, it did not go through this process. As of this commit no lane has been merged yet — `main` holds only this shell — so the evidence is on the open PRs (`gh pr list --state open`) rather than in `main`'s merge history; that history fills in as Trevor merges.

## Model used by the product itself

| Field | Value |
|---|---|
| Provider | Amazon Bedrock |
| Model family | Claude **or** Nova (whichever is enabled on the account) |
| Region | `us-east-1` |
| Exact model id | **TBD** — recorded here once the deployed value is fixed |
| Where the id is configured | `infra/envs/*.tfvars` (`bedrock_model_ids`) and the `BEDROCK_MODEL_ID` environment variable read by `demo-app/`. Never hardcoded in application code |
| What it is used for | One LLM answer per demo flight, over a small local corpus retrieved by a single read-only RAG tool |
| Faking it | `TRACEVAULT_FAKE_BEDROCK=1` makes the demo return a canned response instead of calling Bedrock. If the demo is run that way, say so out loud — see **Demo integrity (P-15)** in the README |
| IAM scope | `bedrock:InvokeModel` limited to the model ids listed in tfvars. No wildcard model access |

The model sees only the demo prompt and the retrieved corpus text. Model output is **contracted** to be stored the same way a prompt is — redacted at ingest, hashed and masked, TTL 7 days — but that ingest path (`vault/`) is not implemented yet, and nothing has been deployed. See **Demo integrity (P-15)** in the README for what is contracted versus built versus deployed.

## Not used

- **No mystery Copilot commits.** Every AI-authored change arrives as a feature-branch PR with a committed handoff and a named agent id. There are no unattributed commits on `main`.
- **No autonomous infrastructure changes.** No agent holds AWS credentials, runs `terraform apply`, or deploys. Deployment happens only from `main` via `deploy.yml` with GitHub OIDC, after Trevor merges. Rollback is a human re-running the last green `deploy.yml`.
- **No agent merges its own work.** Only Trevor merges. `contracts/` changes additionally need all three humans on the thread.
- **No AI in the request path beyond the demo.** TraceVault does not use an LLM to triage, summarise, or auto-remediate traces. Humans read the traces. There is no RCA-via-Bedrock feature.
- **No write-capable agent tools in the product.** The demo agent has exactly one retrieve tool on an allowlist — no write, no delete, no shell.
- **No real customer data.** Demo PII is synthetic.
