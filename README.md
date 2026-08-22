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

**API — live.** `https://55qm437628.execute-api.us-east-1.amazonaws.com`

```console
$ curl https://55qm437628.execute-api.us-east-1.amazonaws.com/health
200 {"ok":true}
```

**Explorer UI — built, not published.** `https://d13b678j60bhap.cloudfront.net` answers **403** at `/`. The distribution is
live, but the web bucket holds only `health.json`; `web/` landed on `main` in #75 and has not been
built and uploaded.

Applied 2026-08-22: 66 managed resources, both vault Lambdas, all five routes. What is *not* live is
listed in **Demo integrity (P-15)** below — including one security control that cannot work as designed.

## Governance, security and evidence

Everything a reviewer needs is in this repository. Nothing required to evaluate TraceVault lives anywhere else.

| Artifact | Where | Status |
|---|---|---|
| Architecture + data flow | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | present |
| Threat model + trust boundaries | [`SECURITY.md`](SECURITY.md) | present |
| Governance / AI system card | [`GOVERNANCE.md`](GOVERNANCE.md) | present |
| AI supply chain inventory | [`docs/AI_INVENTORY.md`](docs/AI_INVENTORY.md) | present |
| AI usage disclosure | [`AI_USAGE.md`](AI_USAGE.md) | present |
| Data classification + abuse cases | `docs/DATA_AND_ABUSE.md` | in progress |
| Runbook | `make help` | present |
| Frozen HTTP + span contract | `contracts/` | present |

Items marked in progress have open issues against them; the tracking issue for the full submission checklist is pinned.

## Lineage — what this builds on

TraceVault is not a greenfield idea. It is a direct response to the AI-observability projects from the two 2025 Canada DevOps Community of Practice hackathons, and the organizers' brief for 2026 asks teams to continue from that work. This section records what we took, what we left, and the gap we exist to close. It is prior-art attribution, not a claim to have shipped their features.

The Ottawa 2025 winner, [`AICommunityofPractice_Observability`](https://github.com/CanadaDevOpsCommunity2025/AICommunityofPractice_Observability), is an umbrella repository that aggregates three projects as submodules. Our theme is the same theme it won on, so it is the branch of the lineage we sit on.

| Prior project | What we took | What we deliberately did not take |
|---|---|---|
| [InnerAI](https://github.com/CanadaDevOpsCommunity2025/AIObservability-Monitoring_InnerAI) (Ottawa, observability umbrella) | The core shape: an SDK wraps the model call and emits spans. A four-way split of emit / store / view / demo user. | Plaintext prompt storage. Localhost-only operation. No tenants. |
| [InsightAI_Minions](https://github.com/CanadaDevOpsCommunity2025/InsightAI_Minions) (Ottawa, observability umbrella) | OpenTelemetry `gen_ai.*` attribute naming, which our span schema uses. CI that deploys the thing judges actually click, not only infrastructure. | Grafana as the product surface. SSH-based deploys. |
| [GenA11yHelper](https://github.com/CanadaDevOpsCommunity2025/GenA11yHelper) (Ottawa, observability umbrella) | Terraform from hour zero. A public URL as a first-class deliverable. Deliberately small scope. | EC2 with port 22. Long-lived `AKIA` access keys. Deploy on every push. |
| [Vulnerability-Resolution-Agent](https://github.com/CanadaDevOpsCommunity2025/Vulnerability-Resolution-Agent) (Toronto winner) | Security proven by a test a judge can watch fail, not by assertion — their HMAC verification suite is the pattern behind our tenant-key and cross-tenant tests. An ingest path isolated from the read path. | The `ngrok` tunnel and IDE-coupled MCP/SSE transport. A datastore with no tenant isolation. |
| [HemoStat](https://github.com/CanadaDevOpsCommunity2025/HemoStat) (Toronto, Impactful) | Freezing the wire contract before lane code — their `docs/API_PROTOCOL.md` is why `contracts/http.md` exists at hour zero. One package per person. `uv` plus a Makefile whose targets skip cleanly when a directory is absent. | Streamlit. Prometheus and Grafana provisioning. Autonomous remediation of live systems. |

### The gap we exist to close

Across the prior work, safe storage of observability data is treated as something you could add later rather than a property of the design. Three concrete instances, from their own documentation and code: InnerAI persisted raw prompts. HemoStat's audit trail carries whatever the emitting event contained, with no redaction step on the way in. VRA's datastore has no tenant boundary. We are not claiming to have audited every line of all five projects — these are the specific, checkable gaps that motivated our design.

TraceVault's contribution is to make two properties structural rather than optional:

- **Write-time redaction, fail-closed.** The raw prompt is masked and hashed before anything is persisted. If redaction cannot complete, ingest returns `400 redaction_failed` and stores **nothing** — the failure mode is data loss, never a leak. **Implemented and tested** (`vault/`, 83 tests).
- **Tenant isolation that returns 403, not 404.** A cross-tenant read is refused as forbidden rather than hidden as missing, so the boundary is observable and testable instead of silently indistinguishable from an empty result. **Implemented, tested and deployed** (`vault/read/tenant_guard.py`, `vault/tests/read/test_isolation.py`); not yet exercised against a live Cognito token — see **Demo integrity (P-15)** below.

Both are frozen in [`contracts/`](contracts/). [`SECURITY.md`](SECURITY.md) maps each to the test that proves it, or states that it is not covered.

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

**As of 2026-08-22 the stack is applied and the API is live.** 66 managed resources, both vault
Lambdas (`vault.handlers.ingest.handler` / `vault.handlers.read.handler`), and all five routes.
Verified against AWS rather than against Terraform's output: `GET /health` → `200`,
`GET /v1/traces` → `401` with no JWT, `POST /v1/traces` → `401` with no tenant key — the
contracted fail-closed behaviour.

Three things are **not** live, and they are the honest gaps:

1. **The Explorer UI is not published.** `web/` is on `main` (#75), but nothing has been uploaded to
   the web bucket, so CloudFront serves 403 at `/`.
2. **No authenticated request has ever been made.** Every check above is unauthenticated. No real
   flight has been ingested, so nothing has been redacted in production, and tenant isolation has not
   been demonstrated end-to-end against a live token — only in tests.
3. **WAF filters nothing.** The web ACL exists but is associated with no resource. See
   [`SECURITY.md`](SECURITY.md).

Verify the built column yourself:

```bash
py -m pytest vault -q                                        # 109 passed
cd sdk && uv run pytest -q                                   # 3 passed
cd demo-app && TRACEVAULT_FAKE_BEDROCK=1 uv run pytest -q     # 2 passed
```

| Piece | Contracted | Built | Deployed | What that means today |
|---|---|---|---|---|
| CloudFront, Cognito, HTTP API, KMS, DynamoDB, S3 | Yes | Yes — `infra/` on `main` | **Yes** — applied 2026-08-22 | 66 managed resources live; `GET /health` → `200` from the public internet. **Exception:** the WAF web ACL exists but is attached to nothing — `aws_wafv2_web_acl_association` cannot target an HTTP API. |
| Redaction on ingest (deny-list, Presidio optional) | Yes — `contracts/http.md` | **Yes** — `vault/redact/` + re-applied in `vault/ingest/` | **Yes** — in both Lambdas | Implemented and tested: fail-closed `redaction_failed` stores nothing, adversarial suite included. Presidio is optional and **absent in CI**, so the tested guarantee is deny-list-driven. The code is deployed, but **no real traffic has been ingested**, so nothing has been redacted in production yet. |
| Ingest API (`POST /v1/traces`) | Yes — `contracts/http.md` | **Yes** — `vault/handlers/ingest.py` | **Yes** — `tracevault-dev-vault-ingest` | Tenant-key auth, schema validation, tenant-scoped writes, S3-then-Dynamo commit order. Live and fail-closed (`401` without a key). **Never exercised with a valid key**, so the write path is proven only against injected fakes. |
| Read + audit API (`GET /v1/traces*`, 403, audit rows) | Yes — `contracts/http.md` | **Yes** — `vault/read/`, `vault/audit/`, `vault/handlers/read.py` (#68, #69, #71) | **Yes** — `tracevault-dev-vault-read` | 403-not-404 has code and tests (`vault/read/tenant_guard.py`, `vault/tests/read/test_isolation.py`). Live and returning `401` without a JWT. **Not yet exercised with a real Cognito token**, so cross-tenant refusal is proven in tests, not in production. |
| Bedrock model call | Yes | Yes — `demo-app/` on `main` | **No** | A real Bedrock call **unless** `TRACEVAULT_FAKE_BEDROCK=1`, which returns a canned response. Every test to date has used the fake. If we demo with it set, we say so out loud. The embedding model is not yet in the IAM allowlist — see [`docs/AI_INVENTORY.md`](docs/AI_INVENTORY.md). |
| Span emission (SDK) | Yes — `contracts/span.schema.json` | Yes — `sdk/` on `main` | **No** | Emits schema-shaped spans with masked preview + `prompt_hash`. |
| Explorer, Day 1 (fixtures) | Yes — `contracts/fixtures/` | **Yes** — `web/` on `main` (#75), Playwright specs | **No** | The fixture-backed explorer renders list, detail, masked PII and the contracted forbidden UI. **Nothing is uploaded to the web bucket**, which holds only `health.json`, so CloudFront serves 403 at `/`. Built, not published. |
| Explorer, Day 2 (live data) | Yes | **Partial** — `web/` renders fixtures; `web/src/lib/cognito.ts` exists | **No** | Both prerequisites now exist (`web/` and a deployed read handler), but the UI is still fixture-backed and has not been pointed at the live API. |
| Ingest URL unset | Yes | Yes — `sdk/` on `main` | n/a | With `TRACEVAULT_INGEST_URL` unset the SDK does **not** POST — it writes `sdk/.last-flight.json` locally and does not crash. That local file is a fallback, **not** the product. |

Demo data is **synthetic** PII only. The privacy properties this product is built to have — raw prompts never persisted, only `prompt_hash` plus a masked `prompt_preview`, DynamoDB TTL 7 days, Lambda logs 7 days — are implemented and tested for the ingest path; the retention values are configured in Terraform and applied, though no assertion re-checks them. Tenant isolation is implemented and tested, and unproven against live traffic. [`SECURITY.md`](SECURITY.md) maps every threat to the test that proves it, or says plainly that it is not covered.

## AI transparency

Which humans used which AI tools, and what the product itself calls: [`AI_USAGE.md`](AI_USAGE.md) (P-06).

## Limitations

Deliberately not built in 48h: custom domain, multi-region, PITR, CloudTrail, GuardDuty, VPC-attached Lambdas, MFA on the judge users, billing dashboards, a pager, and any SOC2 documentation. Judge users are demo tenants, not real customers, and this is not a fleet-KPI dashboard.

## License

See [`LICENSE`](LICENSE).
