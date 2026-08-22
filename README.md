# TraceVault

**AI Application Flight Recorder.** Theme (P-02): **Unified AI Observability**.
Team **Summer.exe** — Team 04, DevOps for GenAI Hackathon Series, Ottawa 2026.

**Problem (P-03):** On-call cannot reconstruct one AI request (LLM, RAG, tools, cost) without the observability stack itself becoming a data leak.

Reconstruct **one** AI request — spans, RAG hops, tokens, `$` — without ever storing a raw prompt or raw PII.

## Outcomes judges can measure

1. Public HTTPS URL; `GET /health` → `200 {"ok":true}`
2. One flight: waterfall + RAG hops + tokens + `cost_usd`
3. Synthetic email/SSN in the prompt → **zero** raw PII at rest; UI shows `REDACTED`
4. `tenant-b` presenting a tenant-a `trace_id` → **403** (not 404); list is tenant-scoped

## Public URL

**TBD — filled by Trevor after the first green `deploy.yml`.**

Until that line holds a real CloudFront URL, treat the deployed product as not yet live. Nothing here invents a hostname.

## Plan, judge bar, scoring

This repo is the **product only**. The plan, the judge click-path, the handbook map (P-01–P-15), the threat model, the system card, and the 100-point rubric live in the team scratchbook and are deliberately **not** duplicated here:

**https://github.com/Sighopss/TVault-scratchbook-accessible** — `PLAN.md` + `JUDGE.md`.

Agents working in this repo still read those two files from that repo before writing code.

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

`make help` **is** the runbook — health check, tenant users, rollback, log locations. Rollback is re-running the last green `deploy.yml`; there is no separate rollback script.

Infrastructure variables: copy `infra/envs/dev.tfvars.example` (or `prod.tfvars.example`) to `dev.tfvars` / `prod.tfvars` and fill your own values. The `*.tfvars.example` files are the only variable documentation that is committed.

**No secrets in git.** Real values live in `TF_VAR_*` environment variables and AWS Secrets Manager. CI authenticates to AWS with **GitHub OIDC** — there is no `AKIA` key anywhere in this repo, and `gitleaks` fails the PR if one appears. `*.tfvars` (without `.example`) is gitignored.

## Demo integrity (P-15)

Stated plainly, because undisclosed mocks are a handbook red flag:

| Piece | Status |
|---|---|
| CloudFront, Cognito, HTTP API, KMS, DynamoDB, S3 | **Live** after `terraform apply` |
| Redaction on ingest (Presidio + deny-list) | **Live** — fail-closed, nothing stored on failure |
| Bedrock model call | **Live** unless `TRACEVAULT_FAKE_BEDROCK=1` — with that set the model response is **faked** and we say so out loud |
| Explorer, Day 1 | **Stub** — renders committed fixtures from `contracts/fixtures/`, not a live API |
| Explorer, Day 2 | **Live** — `GET /v1/traces*` |
| Ingest URL unset | The SDK does **not** POST; it writes `sdk/.last-flight.json` locally and does not crash. That local file is a fallback, **not** the product |

Demo data is **synthetic** PII only. Prompts are never stored raw: only `prompt_hash` plus a masked `prompt_preview`. Trace records expire on a DynamoDB TTL of 7 days; Lambda logs are retained 7 days.

## AI transparency

Which humans used which AI tools, and what the product itself calls: [`AI_USAGE.md`](AI_USAGE.md) (P-06).

## Limitations

Deliberately not built in 48h: custom domain, multi-region, PITR, CloudTrail, GuardDuty, VPC-attached Lambdas, MFA on the judge users, billing dashboards, a pager, and any SOC2 documentation. Judge users are demo tenants, not real customers, and this is not a fleet-KPI dashboard.

## License

See [`LICENSE`](LICENSE).
