# TraceVault

**AI Application Flight Recorder.** Theme (P-02): **Unified AI Observability**.
Team **Summer.exe** — Team 04, DevOps for GenAI Hackathon Series, Ottawa 2026.

**Problem (P-03):** On-call cannot reconstruct one AI request (LLM, RAG, tools, cost) without the observability stack itself becoming a data leak.

Reconstruct **one** AI request — spans, RAG hops, tokens, `$` — without ever storing a raw prompt or raw PII.

## Outcomes judges can measure

These are the four **targets** the build is aimed at, not a claim about what runs today — see **Demo integrity (P-15)** below for what is actually built and deployed right now.

1. Public HTTPS URL; `GET /health` → `200 {"ok":true}`
2. One flight: waterfall + RAG hops + tokens + `cost_usd`
3. Synthetic email/SSN in the prompt → **zero** raw PII at rest; UI shows `REDACTED`
4. `tenant-b` presenting a tenant-a `trace_id` → **403** (not 404); list is tenant-scoped

## Public URL

**TBD — filled by Trevor after the first green `deploy.yml`.**

Until that line holds a real CloudFront URL, treat the deployed product as not yet live. Nothing here invents a hostname.

## Governance, security and evidence

Everything a reviewer needs is in this repository. Nothing required to evaluate TraceVault lives anywhere else.

| Artifact | Where | Status |
|---|---|---|
| Architecture + data flow | `README.md` | in progress |
| Threat model + trust boundaries | `SECURITY.md` | in progress |
| Governance / AI system card | `GOVERNANCE.md` | in progress |
| AI usage disclosure | [`AI_USAGE.md`](AI_USAGE.md) | present |
| Data classification + abuse cases | `docs/DATA_AND_ABUSE.md` | in progress |
| Runbook | `make help` | present |
| Frozen HTTP + span contract | `contracts/` | present |

Items marked in progress have open issues against them; the tracking issue for the full submission checklist is pinned.

## Team

| Name | Role | Lane / paths |
|---|---|---|
| **Trevor Kutto** | Project lead — Recorder + AWS + CI/CD | `sdk/`, `demo-app/`, `infra/`, `scripts/`, `.github/`, `Makefile` |
| **Alexis Mugisha** | Vault | `vault/` |
| **Michael Nwaeze** | Explorer | `web/`, `PRODUCT.md`, `DESIGN.md` |
| **Kim Widya** | Team member | — |
| **Jemaelle Saint-Brice** | Team member | — |

Contact: Trevor Kutto — kuttot@algonquincollege.com — https://github.com/Sighopss

Project name: **TraceVault**. Team name: **Summer.exe**. Registered repo name: `DevOps-for-GenAI---Ottawa-2026---Team-04-Summer.exe`.

## Repo layout — who owns what

`main` is protected. One PR per lane, each PR commits a handoff file (`handoffs/`), and **only Trevor merges**. Do not write another human's tree.

| Path | Owner |
|---|---|
| `contracts/` | All three (schema/HTTP changes need Trevor + Alexis + Michael on the PR) |
| `sdk/`, `demo-app/`, `infra/`, `scripts/`, `.github/`, `Makefile` | Trevor |
| `vault/` | Alexis |
| `web/`, `PRODUCT.md`, `DESIGN.md` | Michael |
| `handoffs/` | One file per PR, per agent |
| `README.md`, `AI_USAGE.md` | Trevor (submission shell) |

This table is the **ownership map**, not an inventory of what exists. Most of these directories are still on open PRs or not started — `git ls-tree main` is the honest answer at any moment, and **Demo integrity (P-15)** below records the state as of this commit.

Two Lambdas only: `vault-ingest` → `vault.handlers.ingest.handler`, `vault-read` → `vault.handlers.read.handler`. The HTTP surface is frozen in `contracts/http.md`; the span shape is `contracts/span.schema.json`. Do not invent a second API.

## Reproduce (P-11)

Toolchain pins — same versions CI uses:

| Tool | Version |
|---|---|
| Python | 3.12 (`uv`) |
| Node | 22 (`pnpm@9`) |
| Terraform | >= 1.9 |
| AWS region | `us-east-1` |

```bash
git clone https://github.com/Sighopss/DevOps-for-GenAI---Ottawa-2026---Team-04-Summer.exe
cd DevOps-for-GenAI---Ottawa-2026---Team-04-Summer.exe
make help          # the runbook: health, tenants, rollback, where logs live
make test          # sdk/ tests   (targets skip cleanly when a lane's directory is missing)
make vault         # vault/ tests
make web           # web/ lint + Playwright
```

`make help` **is** the runbook — health check, tenant users, rollback, log locations. Rollback is re-running the last green `deploy.yml`; there is no separate rollback script. Targets skip cleanly when a lane's directory is missing, which on `main` today means most of them skip: the `Makefile`, `.github/`, `infra/`, `sdk/`, `demo-app/`, and `scripts/` are all still on open PRs, and `vault/` and `web/` do not exist yet. Clone `main` and you get this shell; the commands above become meaningful as Trevor merges each lane.

Infrastructure variables: copy `infra/envs/dev.tfvars.example` (or `prod.tfvars.example`) to `dev.tfvars` / `prod.tfvars` and fill your own values. The `*.tfvars.example` files are the only variable documentation that is committed.

**No secrets in git.** Real values live in `TF_VAR_*` environment variables and AWS Secrets Manager. CI authenticates to AWS with **GitHub OIDC** — there is no `AKIA` key anywhere in this repo, and `gitleaks` fails the PR if one appears. `*.tfvars` (without `.example`) is gitignored.

## Demo integrity (P-15)

Stated plainly, because undisclosed mocks are a handbook red flag. Three different things get confused in a demo, so this table keeps them apart:

- **Contracted** — frozen in `contracts/` (HTTP surface, span schema, fixtures). Agreed, not written.
- **Built** — code exists in this repo. Note what is on `main` versus still on an open PR.
- **Deployed** — running on AWS at a public URL.

**As of this commit, nothing is deployed.** No `terraform apply` has run, `deploy.yml` has not run, and there is no public URL — which is why the **Public URL** line above still says TBD. `main` currently holds only this README, `AI_USAGE.md`, the handoff templates, and `LICENSE`; every lane below is on an open PR awaiting Trevor's merge, or not started.

| Piece | Contracted | Built | Deployed | What that means today |
|---|---|---|---|---|
| CloudFront, Cognito, HTTP API, KMS, DynamoDB, S3 | Yes | Terraform written, open PR (Trevor) | **No** | Terraform exists but has never been applied. There is no live infrastructure and no URL yet. |
| Redaction on ingest (Presidio + deny-list) | Yes — `contracts/http.md` | **No — not yet implemented** | **No** | `vault/` does not exist in this repo. Alexis's lane has not landed and has no open PR. Fail-closed `redaction_failed` with nothing stored is the **contracted** behaviour once it lands — it is not running now, and nothing has been redacted by this product yet. |
| Ingest and read API (`POST /v1/traces`, `GET /v1/traces*`, audit, 403) | Yes — `contracts/http.md` | **No — not yet implemented** | **No** | Same lane as the row above: both Lambdas are Alexis's `vault/`. The routes are frozen and the error JSON is agreed; no handler code exists yet. |
| Bedrock model call | Yes | Demo written, open PR (Trevor) | **No** | When it runs, it is a real Bedrock call **unless** `TRACEVAULT_FAKE_BEDROCK=1`, which returns a canned response. If we demo with that set, we say so out loud. |
| Explorer, Day 1 (fixtures) | Yes — `contracts/fixtures/` | **No — not yet implemented** | **No** | `web/` does not exist in this repo. Michael's lane has not landed. The fixtures it is meant to render (`tenant-a-rag.json`, `tenant-b-forbidden.json`) **are** committed under `contracts/fixtures/`; there is no UI rendering them yet. |
| Explorer, Day 2 (live data) | Yes | **No** | **No** | Depends on both `web/` and `vault/`. Neither exists. This is the plan for Day 2, not a current capability. |
| Ingest URL unset | Yes | Yes — SDK written, open PR (Trevor) | n/a | Accurate as written: with `TRACEVAULT_INGEST_URL` unset the SDK does **not** POST — it writes `sdk/.last-flight.json` locally and does not crash. That local file is a fallback, **not** the product. |

Demo data is **synthetic** PII only. The privacy properties this product is built to have — raw prompts never persisted, only `prompt_hash` plus a masked `prompt_preview`, DynamoDB TTL 7 days, Lambda logs 7 days — are contracted and are the bar the `vault/` tests must prove. They are not yet demonstrated by running code, and this README will not claim they are until that code lands and is deployed.

## AI transparency

Which humans used which AI tools, and what the product itself calls: [`AI_USAGE.md`](AI_USAGE.md) (P-06).

## Limitations

Deliberately not built in 48h: custom domain, multi-region, PITR, CloudTrail, GuardDuty, VPC-attached Lambdas, MFA on the judge users, billing dashboards, a pager, and any SOC2 documentation. Judge users are demo tenants, not real customers, and this is not a fleet-KPI dashboard.

## License

See [`LICENSE`](LICENSE).
