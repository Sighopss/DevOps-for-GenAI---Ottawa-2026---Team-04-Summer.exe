# TraceVault

**AI Application Flight Recorder.** Theme (P-02): **Unified AI Observability**.
Team **Summer.exe** — Team 04, DevOps for GenAI Hackathon Series, Ottawa 2026.

**Problem (P-03):** On-call cannot reconstruct one AI request (LLM, RAG, tools, cost) without the observability stack itself becoming a data leak.

Reconstruct **one** AI request — spans, RAG hops, tokens, `$` — without ever storing a raw prompt or raw PII.

## Outcomes judges can measure

All four are demonstrated against the live deployment as of 2026-08-22 ([`docs/RED_TEAM.md`](docs/RED_TEAM.md)), not just targets the build is aimed at — see **Demo integrity (P-15)** below for exactly what was checked, and the two honest gaps that remain.

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

**Explorer UI — live.** `https://d13b678j60bhap.cloudfront.net/` answers **200** with the TraceVault
welcome screen (Sign in with Cognito). The full flight explorer is built and published at
`/explorer.html` — list, waterfall, masked PII, tenant/audit chrome. One known rough edge: typing or
bookmarking `/explorer` directly (no `.html`) currently falls back to the welcome page instead of the
explorer — only in-app navigation (the welcome page's own links, after sign-in) reaches it today. See
**Demo integrity (P-15)** below.

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
| Data classification + abuse cases | [`docs/DATA_AND_ABUSE.md`](docs/DATA_AND_ABUSE.md) | present |
| Runbook | `make help` | present |
| Frozen HTTP + span contract | `contracts/` | present |

Every artifact above is present on `main`. What is *not* yet true of the deployed system is not hidden in this table — it is named plainly in **Demo integrity (P-15)** and **Limitations** below.

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

- **Write-time redaction, fail-closed.** The raw prompt is masked and hashed before anything is persisted. If redaction cannot complete, ingest returns `400 redaction_failed` and stores **nothing** — the failure mode is data loss, never a leak. **Implemented, tested (`vault/`, 115 tests), and demonstrated against the live deployment** — a planted email/SSN/AWS key came back `[EMAIL]`/`[SSN]`/`[AWS_KEY]` at read *and* at rest, with zero raw hits in S3, DynamoDB, or CloudWatch ([`docs/RED_TEAM.md`](docs/RED_TEAM.md)).
- **Tenant isolation that returns 403, not 404.** A cross-tenant read is refused as forbidden rather than hidden as missing, so the boundary is observable and testable instead of silently indistinguishable from an empty result. **Implemented, tested, deployed, and demonstrated against the live deployment** (`vault/read/tenant_guard.py`, `vault/tests/read/test_isolation.py`) — a tenant-b Cognito ID token requesting a tenant-a `trace_id` returned `403 "tenant mismatch"` with no spans, and tenant-a's flight was absent from tenant-b's list ([`docs/RED_TEAM.md`](docs/RED_TEAM.md) B1/B3).

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

This table is the **ownership map**, not a status report. Every path above is on `main` as of this commit — `git ls-tree main` is the honest answer at any moment, and **Demo integrity (P-15)** below records what is *deployed*, which is a separate question from what is *built*.

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
make test          # sdk/ tests
make vault         # vault/ tests
make web           # web/ lint only (Playwright is `cd web && pnpm test`, not wired into this target)
```

`make help` **is** the runbook — health check, tenant users, rollback, log locations. Rollback is re-running the last green `deploy.yml`; there is no separate rollback script. Targets skip cleanly when a lane's directory is missing — that was true early in the build and stays true as a greenfield safeguard, but every lane (`sdk/`, `demo-app/`, `vault/`, `web/`, `infra/`, `scripts/`, `.github/`, `Makefile`) is on `main` today, so none of the targets above actually skip anymore.

Infrastructure variables: copy `infra/envs/dev.tfvars.example` (or `prod.tfvars.example`) to `dev.tfvars` / `prod.tfvars` and fill your own values. The `*.tfvars.example` files are the only variable documentation that is committed.

**No secrets in git.** Real values live in `TF_VAR_*` environment variables and AWS Secrets Manager. CI authenticates to AWS with **GitHub OIDC** — there is no `AKIA` key anywhere in this repo, and `gitleaks` fails the PR if one appears. `*.tfvars` (without `.example`) is gitignored.

## Demo integrity (P-15)

Stated plainly, because undisclosed mocks are a handbook red flag. Three different things get confused in a demo, so this table keeps them apart:

- **Contracted** — frozen in `contracts/` (HTTP surface, span schema, fixtures). Agreed, not written.
- **Built** — code exists in this repo. Note what is on `main` versus still on an open PR.
- **Deployed** — running on AWS at a public URL.

**As of 2026-08-22 the stack is applied, the API is live, and it has been attacked on purpose.** 66
managed resources, both vault Lambdas (`vault.handlers.ingest.handler` /
`vault.handlers.read.handler`), and all five routes. [`docs/RED_TEAM.md`](docs/RED_TEAM.md) ran a
14-attack harness against the live deployment the same day — 6 unauthenticated (`/health` baseline,
no-token reads, bad ingest key, forged JWT, path traversal, oversize body) and 8 **authenticated**,
using real tenant keys and Cognito ID tokens for `tenant-a`/`tenant-b`: a cross-tenant read (`403`, not
`404`), a live PII flight ingested and read back masked, the raw S3 object and DynamoDB item inspected
directly with zero raw hits, tenant-b list isolation, the audit trail, and a CloudWatch log scrape with
zero matches. 14/14. This is not a claim about tests passing in CI — every row in that harness ran
against the public URL.

Two things are genuinely **not (yet) live**, and they stay named plainly rather than softened:

1. **WAF is attached to CloudFront, but not yet confirmed evaluating traffic.** The original gap —
   WAFv2 cannot attach to an HTTP API, so the association failed on every apply — was fixed the same
   day (#100/#128): the ACL is now `CLOUDFRONT`-scoped and set directly on the distribution's
   `web_acl_id`, confirmed live. What is **not** yet confirmed: ~13 minutes after that apply, an XSS
   and a SQLi payload sent to the edge both still returned `200`, and CloudWatch `AWS/WAFV2`
   `AllowedRequests`/`BlockedRequests` show zero datapoints — consistent with normal edge propagation
   (10–20 min) but not yet observed working. Flood protection until it is confirmed is still the
   in-Lambda caps plus API Gateway throttling, not WAF. See [`docs/RED_TEAM.md`](docs/RED_TEAM.md).
2. **The edge TLS floor is TLSv1, not the requested 1.2.** `infra/cloudfront.tf` asks for
   `minimum_protocol_version = "TLSv1.2_2021"`, but the distribution uses the default CloudFront
   certificate, which silently pins TLSv1 instead — confirmed live against the distribution config.
   Fixing it needs a custom domain plus an ACM certificate. See [`SECURITY.md`](SECURITY.md).

One rough edge in the Explorer itself: navigating **directly** to `/explorer` (typed URL, bookmark, or
a hard refresh while on that page) falls back to the welcome page instead of the flight explorer — only
in-app navigation from `/`, or the exact URL `/explorer.html`, reaches it today. The judge click-path
(sign in from `/`) is not affected; a deep link to `/explorer` is.

Verify the built column yourself:

```bash
py -m pytest vault -q                                        # 115 passed
cd sdk && uv run pytest -q                                   # 6 passed
cd demo-app && TRACEVAULT_FAKE_BEDROCK=1 uv run pytest -q     # 20 passed
```

| Piece | Contracted | Built | Deployed | What that means today |
|---|---|---|---|---|
| CloudFront, Cognito, HTTP API, KMS, DynamoDB, S3 | Yes | Yes — `infra/` on `main` | **Yes** — applied 2026-08-22 | 66 managed resources live; `GET /health` → `200` from the public internet. **Exception:** the WAF ACL is attached to CloudFront (fixed same day, #100/#128) but evaluation against live traffic is not yet confirmed — see Demo integrity above. |
| Redaction on ingest (deny-list, Presidio optional) | Yes — `contracts/http.md` | **Yes** — `vault/redact/` + re-applied in `vault/ingest/` | **Yes** — in both Lambdas | Implemented and tested: fail-closed `redaction_failed` stores nothing, adversarial suite included. Presidio is optional and **absent in CI**, so the tested guarantee is deny-list-driven. **Demonstrated live** — a real email/SSN/AWS-key flight was ingested and read back masked, with zero raw hits reading the S3 object and DynamoDB item directly (`docs/RED_TEAM.md` B2/B2-rest). |
| Ingest API (`POST /v1/traces`) | Yes — `contracts/http.md` | **Yes** — `vault/handlers/ingest.py` | **Yes** — `tracevault-dev-vault-ingest` | Tenant-key auth, schema validation, tenant-scoped writes, S3-then-Dynamo commit order. Live and fail-closed (`401` without a key), and **exercised with a valid key live** — real PII flights ingested by the red-team harness (`docs/RED_TEAM.md` B2). |
| Read + audit API (`GET /v1/traces*`, 403, audit rows) | Yes — `contracts/http.md` | **Yes** — `vault/read/`, `vault/audit/`, `vault/handlers/read.py` (#68, #69, #71) | **Yes** — `tracevault-dev-vault-read` | 403-not-404 has code and tests (`vault/read/tenant_guard.py`, `vault/tests/read/test_isolation.py`) and is **proven live with real Cognito ID tokens**: tenant-b against tenant-a's trace → `403 "tenant mismatch"`, tenant-b's list never shows tenant-a, and audit rows are written on open (`docs/RED_TEAM.md` B1/B3/B4). |
| Bedrock model call | Yes | Yes — `demo-app/` on `main` | **Partial** | IAM allowlist on the OIDC role includes Claude 3.5 Sonnet + Nova Lite + Titan Embed V2 (live 2026-08-22). Nova Lite + Titan Embed V2 invoke in `us-east-1`. Claude 3.5 Sonnet is **EOL on Bedrock** and cannot be enabled; Anthropic still works via Sonnet 4.x inference profiles (roadmap: retarget the allowlist). Demo still defaults to fake in tests (`TRACEVAULT_FAKE_BEDROCK=1`). |
| Span emission (SDK) | Yes — `contracts/span.schema.json` | Yes — `sdk/` on `main` | **No** | Emits schema-shaped spans with masked preview + `prompt_hash`. The library itself is not an AWS resource; it is exercised by `demo-app` and the red-team harness against the live ingest API. |
| Explorer, Day 1 (fixtures) | Yes — `contracts/fixtures/` | **Yes** — `web/` on `main`, Playwright specs | **Yes** — published to the web bucket, served by CloudFront | The fixture-backed explorer renders list, detail, masked PII and the contracted forbidden UI. Live at `/explorer.html`. Direct navigation to `/explorer` (no extension) does not reach it — see the rough edge noted above. |
| Explorer, Day 2 (live data) | Yes | **Yes** — `web/` reads live via `GET /v1/traces*` + `/audit` when a Cognito ID token and `NEXT_PUBLIC_API_URL` are present (`web/src/lib/cognito.ts`) | **Yes** — the deployed build's JS bundle contains the live API and Cognito domain, confirmed by inspecting the published bundle | Both prerequisites exist and are wired together in the deployed build. Not independently re-verified here by signing in as a judge would — that is a manual walkthrough, not a `curl` check. |
| Ingest URL unset | Yes | Yes — `sdk/` on `main` | n/a | With `TRACEVAULT_INGEST_URL` unset the SDK does **not** POST — it writes `sdk/.last-flight.json` locally and does not crash. That local file is a fallback, **not** the product. |

Demo data is **synthetic** PII only. The privacy properties this product is built to have — raw prompts never persisted, only `prompt_hash` plus a masked `prompt_preview`, DynamoDB TTL 7 days, Lambda logs 7 days — are implemented, tested, and demonstrated live against the deployed stack (`docs/RED_TEAM.md`); the retention values are configured in Terraform and applied, though no automated assertion re-checks them as the stack changes. Tenant isolation is implemented, tested, and proven live with real Cognito tokens. [`SECURITY.md`](SECURITY.md) maps every threat to the test that proves it, or says plainly that it is not covered.

## AI transparency

Which humans used which AI tools, and what the product itself calls: [`AI_USAGE.md`](AI_USAGE.md) (P-06).

## Technology inventory

What we run and why. The AI *model* inventory (Bedrock ids, embeddings, inference settings) is separate and authoritative in [`docs/AI_INVENTORY.md`](docs/AI_INVENTORY.md); this table is the surrounding technology.

### Vault — storage and redaction (Alexis)

| Component | Choice | Why this one |
|---|---|---|
| Vault runtime | Python 3.12 on AWS Lambda — two functions only (`vault-ingest`, `vault-read`) | Two entry points map to the two trust levels: an ingest key that can only write, and a Cognito ID token that can only read its own tenant. Fewer functions means fewer IAM roles to reason about. |
| Redaction (authoritative) | Deny-list in `vault/redact/` — email, SSN (three formats), AWS `AKIA`/`ASIA` keys, `sk-` secrets | Deterministic, stdlib-only regex with no model to download or fail. The judge-path guarantee cannot depend on an ML service being reachable at request time. Fails closed: unmaskable input returns `400 redaction_failed` and stores nothing. |
| Redaction (optional) | Presidio — **declared absent in production** (#84) | Lazily imported and not packaged in the Lambda; if present it is a best-effort second pass, and it fails closed if it errors mid-analysis. No guarantee depends on it. See [`docs/DATA_AND_ABUSE.md`](docs/DATA_AND_ABUSE.md). |
| At-rest payloads | S3, SSE-KMS (customer-managed key, rotation on), keys `{tenant_id}/{trace_id}/` | The tenant prefix is enforced twice — by the key layout and by an IAM policy that only permits `PutObject` under it — so a bug in one layer is not sufficient to cross tenants. |
| At-rest index | DynamoDB, PK `tenant_id` / SK `t#{trace_id}`, TTL `expires_at` 7 days | Tenant is the partition key, so a cross-tenant read is not a filter that can be forgotten — it is a different partition. Audit rows share the table under `a#{trace_id}#…`, inheriting the same encryption and TTL. |
| Secrets | AWS Secrets Manager, one secret per tenant | Ingest keys are rotatable without a deploy; a constant-time compare resolves the header, and unreadable or placeholder secrets authenticate nobody. |
| Vault tests | `pytest` (115) + `bandit`, no AWS in unit tests | boto3 is imported lazily and tests inject boto3-shaped fakes, so the suite runs on a bare `pip install pytest bandit` — which is exactly what CI has. |

*Trevor owns the remaining rows of this section (Python/uv SDK + demo-app, Next.js 15 Explorer, Terraform, AWS edge/API services, GitHub Actions + OIDC, pinned versions, SBOM and `trivy` posture) and the assembly of this section — see #55.*

## Limitations

Deliberately not built in 48h: custom domain, multi-region, PITR, CloudTrail, GuardDuty, VPC-attached Lambdas, MFA on the judge users, billing dashboards, a pager, and any SOC2 documentation. Judge users are demo tenants, not real customers, and this is not a fleet-KPI dashboard.

### Vault — known limits and where they go next

- **Redaction is a deny-list, and a deny-list is a known set.** It masks the entities we contracted for — email, SSN, AWS keys, `sk-` secrets — verified against the live store with zero raw hits ([`docs/RED_TEAM.md`](docs/RED_TEAM.md)). It does not claim to catch a person's name or a novel identifier format. *Next:* ship Presidio in the Lambda for named-entity coverage as a second pass, keeping the deny-list authoritative so the guarantee never depends on a model.
- **Reads paginate, and are bounded at 50 flights.** `GET /v1/traces` walks every DynamoDB page before sorting, so a tenant's list and a trace's audit trail are complete rather than silently truncated at the first ~1 MB page (#99). The response is then capped at 50 by contract. *Next:* a cursor on the list endpoint so an operator can page past the newest 50.
- **No per-tenant ingest rate limit.** Flood damage is bounded by the in-Lambda caps — batch ≤100 spans, 1 MB body, 10k-char field, depth-32 nesting — plus API Gateway throttling and the 7-day TTL. The WAF ACL is now attached to CloudFront (#100/#128) but not yet confirmed evaluating traffic. *Next:* per-key usage plans, and confirming the WAF ACL actually filters (`AWS/WAFV2` `BlockedRequests` should show non-zero datapoints after a deliberate bad request).
- **Retention is a flat 7 days for every tenant.** TTL is set per item at ingest, so a per-tenant policy is a configuration change rather than a redesign. *Next:* retention as a tenant attribute, plus an S3 lifecycle rule matching the DynamoDB TTL (today an expired flight's payload is unreachable, because reads resolve through the index item, but the object itself is not yet expired).
- **Audit records reads, not exports.** Every trace open writes an actor/tenant/trace/timestamp row. There is no separate event for "an operator copied this off-screen" — that is outside what an API can observe.

## License

See [`LICENSE`](LICENSE).
