# Handoff — `trevor-docs` — `product-shell`

- Date: 2026-08-21
- Human: `Trevor`
- Agent id: `trevor-docs`
- Branch: `trevor/docs/product-shell`
- PR: `37`
- Mission file: Submission shell — product README, `AI_USAGE.md` (P-06), in-tree handoff template. Scratchbook `PLAN.md` **Submission pack (D2 PM)** + **Handbook (2026)**; no scratchbook mission file for this one.

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
README.md
AI_USAGE.md
handoffs/README.md
handoffs/PR.example.md
handoffs/trevor-docs-product-shell.md
```

## Do not touch

```
contracts/
sdk/
demo-app/
infra/
scripts/
.github/
Makefile
vault/
web/
PRODUCT.md
DESIGN.md
```

## Safe to run in parallel with

All five open lane PRs — none of them claims a path on this branch. Checked `gh pr list --state open` before writing: `trevor-ci` #27 (`.github/`, `Makefile`, `.gitignore`), `trevor-sdk` #28 (`sdk/`), `trevor-infra` #29 (`infra/`), `trevor-demo` #30 (`demo-app/`), `trevor-scripts` #31 (`scripts/`), plus `trevor-contracts` #26 (`contracts/`). Zero overlap. Alexis (`vault/`) and Michael (`web/`, `PRODUCT.md`, `DESIGN.md`) are also unaffected — this PR does not enter their trees.

## Handbook evidence (required — 2026 workbook)

Empty = incomplete PR. Copy from PLAN **Rubric 100** / P-ids.

- Lifecycle stage: `Govern` — submission-pack evidence (`PLAN.md` → **Submission pack (D2 PM)**, items 2, 5, 7–8, 19).
- P-ids this PR moves: `P-02` (one theme named in the product README), `P-04` (live-use-case URL line, explicitly TBD until deploy), `P-06` (`AI_USAGE.md` now exists in the **product** repo, which is where the handbook requires it), `P-11` (reproducible: pinned toolchain, `infra/envs/*.tfvars.example`, `make help` as the runbook, no secrets in git), `P-15` (demo-integrity table: fixtures vs live vs faked Bedrock, stated in the README rather than only on stage).
- Rubric rows (pts): `Presentation 5` (P-15 stubs stated in writing, so the 3-minute path does not have to remember them), `Team & AI-tool 5` (roster, feature-PR + handoff process, Trevor-merges, `AI_USAGE.md`), `DevOps 10` (reproduce section names the OIDC/no-AKIA rule and rollback = re-run last green `deploy.yml`).
- Tests / attack shown: **None — this PR is documentation only.** It adds no code path, no route, no Terraform, no workflow, so there is nothing to test and no attack to demonstrate. The security-relevant claims it makes (fail-closed redaction, 403 not 404, no PII at rest) are tested by Alexis under `vault/`, not here. `gitleaks` still runs on this PR and passes: no keys, no passwords, no invented hostnames.
- Stub/live (P-15): The **Public URL** line in `README.md` is `TBD — filled by Trevor after the first green deploy.yml`. It is deliberately not a hostname, because no deploy has run. The demo-integrity table splits every piece three ways — **contracted** (frozen in `contracts/`), **built** (code in this repo, on `main` or on an open PR), **deployed** (running on AWS) — and states outright that **nothing is deployed** as of this commit: no `terraform apply`, no `deploy.yml` run, no URL. Redaction, the ingest/read API, and both Explorer days are recorded as **not yet implemented** — `vault/` and `web/` exist on no branch (verified with `git ls-tree` across all refs), so fail-closed `redaction_failed` and the 403 are contracted behaviour, not running behaviour. `TRACEVAULT_FAKE_BEDROCK=1` is disclosed as a faked model call; the unset-ingest-URL fallback to `sdk/.last-flight.json` is accurate against the SDK code on PR #28. The exact Bedrock model id in `AI_USAGE.md` is `TBD` until the deployed value is fixed.
- Judge bar (`JUDGE.md`): never-kill still intact. This PR changes **no code path**, so redaction, 403-not-404, HTTPS URL, fixture UI, `/health`, CORS = CloudFront only, JWT `custom:tenant_id`, one retrieve tool, and ingest key ≠ user JWT are all untouched. It also satisfies the JUDGE.md checklist item "you did not add `PLAN.md` / `JUDGE.md` / `START.md` to the product repo" — this branch adds none of them, and instead links to them in the scratchbook.

## What I shipped

- files:
  - `README.md` — replaced the raw registration roster with the thin product README the plan asks for: product + theme (P-02), one-line problem (P-03), four measurable outcomes, **Public URL: TBD**, pointer to the scratchbook for plan/judge bar/scoring, formatted team roster (all five registered names kept, plus Trevor's e-mail and GitHub), repo-layout ownership table, **Reproduce** (Python 3.12 + `uv`, Node 22 + `pnpm@9`, Terraform ≥ 1.9, `infra/envs/*.tfvars.example`, `make help` = runbook, no secrets in git), **Demo integrity (P-15)**, and a limitations list drawn from the do-not-build fence.
  - `AI_USAGE.md` — new. P-06 evidence file: what it is and which handbook item it satisfies, the `Human | Tool / model | What it produced | Human review` table with Trevor's row pre-seeded from what this repo actually shows (one Claude-based agent per lane, one PR + committed handoff each, human merge), a **Model used by the product itself** section (Amazon Bedrock Claude or Nova, `us-east-1`, id in `infra/envs/*.tfvars` / `BEDROCK_MODEL_ID`, exact id `TBD`), and a **Not used** section (no mystery Copilot commits, no autonomous infra changes, no agent self-merge, no LLM in the triage path, no write-capable agent tools, no real customer data).
  - `handoffs/README.md` — in-tree copy of the scratchbook original so agents working in this repo have the collision procedure without cloning the scratchbook. Header states the canonical copy lives in the scratchbook and must not be duplicated; scratchbook-relative links to `PLAN.md` / `JUDGE.md` rewritten to absolute GitHub URLs, since those files do not and must not exist here. The `PR.example.md` link stays relative — that file now exists in this tree.
  - `handoffs/PR.example.md` — in-tree copy of the template, same header and link treatment. Full section list kept intact, including the **Handbook evidence** block and its `Judge bar (JUDGE.md)` row. The mission-file line now says the mission lives in the scratchbook.
  - `handoffs/trevor-docs-product-shell.md` — this file.
- outputs / env **names** (no secret values):
  - `BEDROCK_MODEL_ID` — demo-app model id; value in `infra/envs/*.tfvars` (`bedrock_model_ids`), recorded in `AI_USAGE.md` once fixed.
  - `TRACEVAULT_FAKE_BEDROCK` — `1` means the model call is faked; documented as a stub in the README.
  - `TRACEVAULT_INGEST_URL` — unset means the SDK writes `sdk/.last-flight.json` instead of POSTing.
  - `TF_VAR_*` — Terraform variable values; never in git.
  - Public URL: **TBD**, filled by Trevor after the first green `deploy.yml`.
- tests: none. Documentation-only PR — see Handbook evidence above.

## What I need

- from whom: **Trevor** — one value and one merge. **Alexis** and **Michael** — one table row each.
- contract / URL / header / path:
  - Trevor: after the first green `deploy.yml`, replace the `TBD` on the **Public URL** line in `README.md` with the CloudFront HTTPS URL, and replace the `TBD` model id in `AI_USAGE.md` with the id actually deployed from `infra/envs/*.tfvars`. Both are single-line edits; no other part of either file needs to change.
  - Alexis: append your own row to the **How humans used AI** table in `AI_USAGE.md` before submission — tool + model, what it produced under `vault/`, how you reviewed it. Do not let anyone else write your row.
  - Michael: same, for `web/`, `PRODUCT.md`, `DESIGN.md`, and Playwright. The README's Demo integrity table currently records Explorer Day 1 and Day 2 as **not yet implemented**, because `web/` does not exist on any branch. When your lane lands, that table needs its rows moved from "not implemented" to "built" — tell Trevor, or update the two rows on your own PR.
  - Alexis, second ask: the same table records redaction and the ingest/read API as **not yet implemented** and marks fail-closed `redaction_failed` / 403-not-404 as *contracted* rather than running. When `vault/` lands, those rows move to "built", and they only become "deployed" after a green `deploy.yml`. Do not let anyone flip them early — that table is the P-15 disclosure a judge is most likely to test.
  - Everyone: use `handoffs/PR.example.md` from **this** repo now. Do not copy `PLAN.md`, `JUDGE.md`, `START.md`, `AGENTS.md`, the Handbook text, or Rubric 100 into this repo; link to the scratchbook instead.

## Blocked on

`nobody`

## Contract reminder

Documentation shell only. This PR owns `README.md`, `AI_USAGE.md`, and the two handoff templates — it defines no API, no schema, and no infrastructure. The HTTP surface stays `contracts/http.md` and the span shape stays `contracts/span.schema.json`; where this README describes routes, tenants, redaction, or `/health`, it is restating those contracts, never amending them. If a contract changes, `contracts/` is edited first and this README follows. Scoring text (Handbook P-01–P-15, threat model, system card, Rubric 100, judge click-path) stays in the scratchbook by rule; the product repo carries only the thin README plus `AI_USAGE.md`.

## Pickup prompt (paste into the other LLM)

```
Read this handoff, then scratchbook PLAN.md and JUDGE.md
(https://github.com/Sighopss/TVault-scratchbook-accessible).
Do not edit the claimed paths above: README.md, AI_USAGE.md,
handoffs/README.md, handoffs/PR.example.md.
Copy handoffs/PR.example.md from THIS repo for your own PR and fill it completely,
including the Handbook evidence block.
Alexis / Michael: append only your own row to the table in AI_USAGE.md.
Do not add PLAN.md, JUDGE.md, START.md, or skills/ content to this repo.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
