# Handoff — `trevor-governance` — `evidence-pack`

- Date: 2026-08-22
- Human: `Trevor`
- Agent id: `trevor-governance`
- Branch: `trevor/docs/governance-evidence`
- PR: TBD
- Mission file: no scratchbook mission file — this PR closes four numbered issues (#40, #41, #42, #43) against Handbook §2/§3/§4 and submission items 4, 7, 9, 11.

Closes #40. Closes #41. Closes #42. Closes #43.

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
SECURITY.md
GOVERNANCE.md
docs/ARCHITECTURE.md
docs/AI_INVENTORY.md
README.md
AI_USAGE.md
handoffs/trevor-governance-evidence-pack.md
```

Checked `gh pr list --state open` before writing: **zero open PRs**. All eleven prior PRs (#26–#65) are merged. The stale `trevor-docs` lease in `.agent-leases.json` claiming `README.md` belongs to merged PR #37 and is not a live conflict.

## Do not touch

```
sdk/  demo-app/  infra/  scripts/  .github/  Makefile   (other Trevor lanes)
vault/                                                   (Alexis)
web/  PRODUCT.md  DESIGN.md                              (Michael)
contracts/                                               (all three)
docs/DATA_AND_ABUSE.md                                   (Alexis — issue #39)
```

This PR reads `vault/`, `infra/`, `sdk/`, and `demo-app/` extensively to cite them. It writes none of them.

## Safe to run in parallel with

Anything not writing `README.md`, `AI_USAGE.md`, or the four new documents. Alexis's read/audit lane (#15, #16, #18) and Michael's `web/` lane do not overlap. **Note for Alexis:** when the read path lands, three rows in `SECURITY.md` and one in the README P-15 table move from "not covered" to a real test path — do not let anyone flip them before the tests exist.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Design` (#40 architecture, #41 threat model) and `Govern` (#42 system card, #43 AI inventory). Both gates were previously unmet in this repo: Design's gate is *threat model + trust boundaries*, Govern's is *human oversight + escalation*, and neither artifact existed.
- P-ids this PR moves: `P-05` (production path — architecture + deployment path now in-repo), `P-07` (security by design — threat model with per-threat test evidence), `P-08` (governance — system card, all nine §4 areas), `P-12` (responsible AI — oversight, transparency, data governance), `P-14` (supply chain — the **AI** supply chain, distinct from the trivy/SBOM software one), `P-15` (demo integrity — the P-15 table was **materially stale** and is corrected here).
- Rubric rows (pts): `Security 15` (§8 asks "top threats and how were they tested" — every row names a test path or admits the gap, which is the direct answer to the *generic security claims* red flag), `AI Governance 10` (all nine §4 areas, every one with a named owner, answering "who owns this and what happens when it fails" against the *no accountability* red flag), `Engineering 15` (architecture + dependencies + deployment path, §5 Production Readiness row 1), `Innovation 10` and `Problem & Impact 15` (the **Lineage** section — novelty measured against named prior art rather than asserted), `Presentation 5` (P-15 corrected so the 3-minute path does not have to remember what changed).
- Tests / attack shown: **This PR is documentation only — it adds no code path, route, Terraform, or workflow, so it introduces nothing to test.** What it does instead is *verify* claims, mechanically:
  - All **29** Python test paths cited in `SECURITY.md` were checked to exist, and every `file::test_name` was checked to resolve to a real `def test_...`. One deliberate exception: `vault/handlers/read.py` is cited *as absent*.
  - All **31** non-Python paths cited across the four documents (workflows, `infra/*.tf`, `contracts/`, corpus, lockfiles, `.bandit`) verified to exist.
  - Every numeric claim verified against source: throttle 10/20 (`infra/variables.tf`), Lambda 30 s / 512 MB, log retention 7 d and alarm 5-in-5-min (`infra/cloudwatch.tf`), `maxTokens` 256 / `temperature` 0 / `max_attempts` 1 / timeouts 5 s and 30 s (`demo_app/bedrock.py`), `RETRIEVE_TOP_K = 2`, `_DEFAULT_TTL_DAYS = 7` (`vault/ingest/pipeline.py`).
  - Least-privilege claims verified negatively: no `s3:DeleteObject` on the ingest role, and no `"s3:*"` / `"dynamodb:*"` / `"bedrock:*"` wildcard in `infra/iam.tf` or `infra/oidc.tf`.
  - The mermaid diagram was **rendered** with `@mermaid-js/mermaid-cli` 11.16.0 (45 KB SVG) to prove it parses, satisfying #40's "renders on GitHub" criterion. Temp artifacts deleted.
  - All relative links in all six touched files resolved from their own directory — zero broken.
  - Suites re-run on `main` to ground the status claims: `vault` **83 passed**, `sdk` **3 passed**, `demo-app` (`TRACEVAULT_FAKE_BEDROCK=1`) **2 passed**.
- Stub/live (P-15): No stub introduced. This PR's contribution to demo integrity is *correcting* the table — see below. `TRACEVAULT_FAKE_BEDROCK=1` is now disclosed in three additional places (`docs/AI_INVENTORY.md`, `AI_USAGE.md`, the corrected P-15 row) including the fact that **every test in the repo runs in fake mode**, which the README did not previously say.
- Judge bar (`JUDGE.md`): never-kill intact — no code path changes, so redaction, 403-not-404, HTTPS URL, fixture UI, `/health`, CORS, JWT `custom:tenant_id`, one retrieve tool, and ingest-key ≠ user-JWT are all untouched. This PR *documents* the boundary rather than altering it. It adds no `PLAN.md` / `JUDGE.md` / `START.md` to the product repo and links to the scratchbook instead.

## What I shipped

- `docs/ARCHITECTURE.md` (**#40**) — mermaid flowchart of browser → CloudFront → Cognito; CloudFront → HTTP API + WAF; demo → Bedrock; demo → `POST /v1/traces` with `X-Tenant-Key`; API → the two Lambdas; ingest → S3 SSE-KMS + DynamoDB TTL 7 d. The **trust boundary is drawn, not implied**: a side-by-side table of write-path vs read-path credential, and two consequences spelled out — that the gateway does **not** enforce tenant isolation (the JWT authorizer only proves the token is real; the 403 is application logic in `vault-read`), and that the **ID** token is required because an access token carries no `custom:tenant_id` yet still passes the authorizer. Also documents the third boundary (the SDK preview is a hint; ingest redaction is authoritative), the five-step write path with the Dynamo commit point, and the deployment path Terraform → approved apply → `deploy.yml` on `main` → CloudFront URL, with rollback = re-run last green.
- `SECURITY.md` (**#41**) — threat → mitigation → **test that proves it** → owner. Twenty-one rows covering every threat class the issue named plus five it did not (cross-tenant *write*, partial-write visibility, error-message leakage, retention beyond purpose, unaudited access). Runnable commands at the top. Three trust boundaries named explicitly. Where there is no test, the cell says so and names the issue — **six rows are honest gaps**, most importantly that 403-not-404 has no code and no test.
- `GOVERNANCE.md` (**#42**) — all nine §4 areas: Purpose & Scope, Risk Classification (with a risk table and the explicit note that the control for the *highest* risk is built while the control for the second-highest is not), Data Governance (including a per-field classification table), Human Oversight (structural — one read-only tool means no high-impact action is reachable, so there is nothing to gate a confirmation on), Transparency, Model/Provider, Monitoring (with the 10x-bottleneck answer), Change Management, Incident Response. **Every incident row names a person**; escalation terminates at Trevor. Accountable owner named at the top with contact details.
- `docs/AI_INVENTORY.md` (**#43**) — models with pinned versions, key inference settings, the corpus as a dataset with provenance ("written by us", not scraped or licensed), every external service, and an explicit *not used* section (no third-party model API, no vendored weights, nothing fine-tuned, no model in the vault's request path). Opens with a three-way disambiguation table so the AI inventory, the human tool disclosure, and the software SBOM cannot be confused. Documents that Presidio is optional, absent in CI, and that **no judged guarantee depends on it**.
- `README.md` — four edits:
  1. Governance table: the four new artifacts flip `in progress` → `present` and become links. `docs/DATA_AND_ABUSE.md` stays `in progress` (Alexis, #39).
  2. **Corrected the stale P-15 table** — see below.
  3. Added **Lineage**, carried forward from merged PR #37's branch where it was stranded (written in an earlier session, links re-verified, and the two bullets now carry accurate build status: redaction *implemented and tested*, isolation *contracted only*).
  4. Added runnable verify commands under P-15 so the built column is checkable, not asserted.
- `AI_USAGE.md` — two stale claims fixed and the #43 cross-reference added: a callout stating this file is the **tool** disclosure and `docs/AI_INVENTORY.md` is the **model** inventory, with the reason they are kept apart. Permitted model ids, embedding-model gap, and key inference settings now recorded. Removed "no lane has been merged yet" and "that ingest path is not implemented yet" — both false as of this commit.

### Two findings, neither invented by this PR

**1. The P-15 demo-integrity table was materially false, in the understating direction.** It claimed `main` held "only this README, `AI_USAGE.md`, the handoff templates, and `LICENSE`", that `vault/` "does not exist in this repo", and that redaction and ingest were "not yet implemented". All eleven PRs merged before this branch was cut; `vault/redact/`, `vault/ingest/`, `vault/store/`, and `vault/handlers/ingest.py` are on `main` with 83 passing tests. **Why this mattered more than a typo:** P-15 is the disclosure a judge is most likely to probe, and a self-assessment wrong in *either* direction destroys the credibility of the whole document. A judge reading "`vault/` does not exist" and then running `ls vault/` has no reason to trust the security claims either — and those are the load-bearing ones. The table was disclaiming our strongest evidence. Corrected row by row, with the read/audit gap kept prominent because it is still real.

**2. The embedding model is unpinned and unauthorised.** `bedrock_model_ids` (which generates the IAM policy in `infra/oidc.tf`) contains only the two **converse** models. `demo_app.bedrock.embed_texts` requires `BEDROCK_EMBED_MODEL_ID` and calls `InvokeModel` on it. The *action* is granted; the *resource* is not — so a live run with `TRACEVAULT_FAKE_BEDROCK` unset would fail the RAG step with `AccessDeniedException`. It has never been hit because every test and every local run so far has used fake mode. This is exactly the defect class an inventory exercise exists to surface: the model was never named, so it was never authorised. Recorded in `docs/AI_INVENTORY.md`, cross-referenced from `SECURITY.md`, `GOVERNANCE.md`, and `AI_USAGE.md`. **Needs a one-line fix in `infra/` before any live Bedrock demo** — not made here, because `infra/` is not this PR's claimed path.

Also noted, lower severity: the live converse path hardcodes `cost_usd = 0.0`, so real spend is not computed per span even though `cost_usd` is carried end to end and judge metric 2 is "tokens + `$`". And S3 payload objects outlive the DynamoDB summary because no bucket lifecycle rule exists — masked content only, so not a PII exposure, but it contradicts a plain reading of "7 day retention". Both recorded in `GOVERNANCE.md` under Monitoring and Data Governance respectively, both owned by Trevor, neither fixed here.

## What I need

- from whom: **Trevor** — review and merge; then fix the embedding-model allowlist in `infra/envs/*.tfvars` + `variables.tf` before any live Bedrock run.
- from whom: **Alexis** — when `vault/read` + `vault/audit` land (#15, #16, #18), four cells become real test paths: the cross-tenant-read row and the unaudited-access row in `SECURITY.md`, the read/audit row in the README P-15 table, and the cross-tenant-read risk row in `GOVERNANCE.md`. Also: `docs/DATA_AND_ABUSE.md` (#39) is yours and is the one remaining `in progress` row in the README governance table.
- from whom: **Michael** — `GOVERNANCE.md` §5 Transparency lists what the UI must tell a user (`REDACTED`, model, tokens, cost, TTL, tenant badge, welcome-page limitation line). Those are requirements sourced from #59 and #62, marked *not built yet*. When `web/` lands, that section describes delivered behaviour and should say so.
- contract / URL / header / path: none. This PR defines no API, schema, or infrastructure. Where it describes routes, tokens, or redaction it is restating `contracts/`, never amending it.

## Blocked on

`nobody`.

## Contract reminder

Documentation and governance evidence only. The HTTP surface stays `contracts/http.md` and the span shape stays `contracts/span.schema.json`. Scoring text (P-01–P-15 map, Rubric 100, judge click-path) stays in the scratchbook by rule; this PR adds product-governance artifacts, which the handbook requires to live **in the product repo**, and links to the scratchbook for planning material. Nothing here claims a control is running when it is only configured — every such row says *reviewed-not-verified* and names the apply issue (#48).