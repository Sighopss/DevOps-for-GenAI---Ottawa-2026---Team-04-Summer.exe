# Handoff — `trevor-supplychain` — `sha-pin`

- Date: 2026-08-22
- Human: `Trevor`
- Agent id: `trevor-supplychain`
- Branch: `trevor/ci/sha-pin`
- PR: TBD
- Mission file: no scratchbook mission file — closes issue #64.

Closes #64.

## Claimed paths (collision)

```
.github/workflows/
Makefile
handoffs/trevor-supplychain-sha-pin.md
```

Checked `gh pr list --state open` before writing. One open PR, **#66** (`trevor/docs/governance-evidence`), which claims `SECURITY.md`, `GOVERNANCE.md`, `docs/`, `README.md`, `AI_USAGE.md`. **Zero overlap** with this branch.

## Do not touch

```
sdk/  demo-app/  infra/  scripts/   (other Trevor lanes)
vault/                              (Alexis)
web/  PRODUCT.md  DESIGN.md         (Michael)
contracts/                          (all three)
SECURITY.md  GOVERNANCE.md  docs/  README.md  AI_USAGE.md   (open PR #66)
```

## Safe to run in parallel with

PR #66 (documentation only, no workflow or Makefile changes). Alexis's read/audit lane and Michael's `web/` lane. Not with another writer of `.github/`.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: `Deploy` — this is the *protect CI/CD and artifacts* half of the supply-chain control, which sits on the Deploy gate (scans + rollback/approval approach).
- P-ids this PR moves: `P-13` (no secrets in git / CI trust), `P-14` (supply chain).
- Rubric rows (pts): `Security 15` (§3 Software Supply Chain — "scan dependencies/images **and protect CI/CD/artifacts**"; the scanning half was already green via trivy, this is the protection half), `DevOps 10` (§8 Supply chain judge check — *"How are dependencies/artifacts trusted?"*, strong evidence *provenance*).
- Tests / attack shown: **The threat is a repointed tag, and it is now blocked two ways.**
  - **Pins.** All **28** `uses:` references across all **7** workflows moved from moving tags to full 40-character commit SHAs, each with the exact semver in a trailing comment. Every SHA was resolved through `gh api repos/OWNER/REPO/git/ref/tags/TAG`, **annotated tags dereferenced** to their commit (three were annotated: `trivy-action`, `configure-aws-credentials`, `pnpm/action-setup`), then confirmed to exist with `repos/OWNER/REPO/commits/SHA`, and finally reverse-resolved to the exact semver so the comment is accurate rather than approximate — `v4` became `v4.4.0`, `v5` became `v5.6.0`, `v4` for `upload-artifact` became `v4.6.2`, and so on.
  - **Guard.** A new step in `trivy.yml` (no path filter, runs on every PR) fails the build if any third-party action is not SHA-pinned or if a pin placeholder returns. Verified with a six-case local harness before commit: passes on the real tree; fails on a moving tag, on a reintroduced placeholder comment, and on a truncated SHA; ignores local `./` composite actions; passes a valid pin carrying a version comment. Harness deleted after use.
  - **YAML.** All seven workflows re-parsed with PyYAML after editing — 0 invalid. `Makefile` checked mechanically for tab-indented recipes, balanced quotes, and no lone `$` (121 recipe lines, clean) because `make` is not installed on this box.
- Stub/live (P-15): No stub. Workflows are live GitHub Actions. Nothing about deploy behaviour changed — only the provenance of the actions it runs.
- Judge bar (`JUDGE.md`): never-kill intact. No application code, route, schema, or Terraform touched, so redaction, 403-not-404, HTTPS URL, fixture UI, `/health`, CORS, JWT `custom:tenant_id`, one retrieve tool, and ingest-key ≠ user-JWT are all untouched. This PR changes which commit of a third-party action runs, and adds one guard step.

## What I shipped

- **All 28 `uses:` pinned**, TODO comments removed rather than left beside the pins:

  | Action | Was | Now | Exact version |
  |---|---|---|---|
  | `actions/checkout` | `@v4` | `11d5960a326750d5838078e36cf38b85af677262` | v4.4.0 |
  | `actions/setup-node` | `@v4` | `49933ea5288caeca8642d1e84afbd3f7d6820020` | v4.4.0 |
  | `actions/setup-python` | `@v5` | `a26af69be951a213d495a4c3e4e4022e16d87065` | v5.6.0 |
  | `actions/upload-artifact` | `@v4` | `ea165f8d65b6e75b540449e92b4886f43607fa02` | v4.6.2 |
  | `aquasecurity/trivy-action` | `@v0.36.0` | `ed142fd0673e97e23eac54620cfb913e5ce36c25` | v0.36.0 |
  | `astral-sh/setup-uv` | `@v10.0.1` | `20cfd1bf945f4377ade1205e4dbc17946fc9a30d` | v10.0.1 |
  | `aws-actions/configure-aws-credentials` | `@v4` | `7474bc4690e29a8392af63c5b98e7449536d5c3a` | v4.3.1 |
  | `gitleaks/gitleaks-action` | `@v3` | `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` | v3.0.0 |
  | `hashicorp/setup-terraform` | `@v3` | `b9cd54a3c349d3f38e8881555d616ced269862dd` | v3.1.2 |
  | `pnpm/action-setup` | `@v4` | `b906affcce14559ad1aafd4ab0e942779e9f58b1` | v4.3.0 |

- **`deploy.yml` verified first**, as the issue required — it is the only workflow holding the OIDC deploy role. Its 12 `uses:` lines are pinned, including all three `configure-aws-credentials` occurrences (`apply-dev`, `apply-prod`, `web`). A hijacked tag there would have been a live AWS credential, not a failed build.
- **New guard step in `trivy.yml`** — `Actions are SHA-pinned (supply chain)`. Runs on every PR because `trivy.yml` has no path filter, so it also catches a regression introduced by a PR that touches nothing else.
- **`Makefile` runbook section** — `Updating a pinned GitHub Action (supply chain)`. Gives the exact two-step `gh api` sequence to resolve a tag *and dereference an annotated one*, states the requirement to verify the SHA belongs to the tag you expect, and requires updating the version comment alongside the SHA so it never goes stale. Explains *why* using the `configure-aws-credentials` blast radius, so the next person does not quietly revert it for convenience.

### One thing worth flagging: the first version of this guard failed itself

The initial implementation grepped for the bare substring `uses:`. Because the guard lives *in* `.github/workflows/trivy.yml`, it matched its own explanatory comment and its own shell body (`ref="${line#*uses:}"`), and its repo-wide grep for the placeholder string matched the placeholder text inside its own error message. It reported four false failures on a correctly pinned tree.

Fixed by matching only real YAML step keys — `^[[:space:]]*-?[[:space:]]*uses:[[:space:]]` — and by assembling the placeholder needle at runtime so the literal string never appears in the file. Both properties are covered by cases 1 and 3 of the harness. Recording it because a guard that cries wolf gets deleted by the next person in a hurry, and because it is a good argument for testing CI logic locally rather than discovering it on a PR.

## What I need

- from whom: **Trevor** — review and merge. No coordination needed with PR #66; the two do not touch a shared file.
- from whom: nobody else. Alexis and Michael are unaffected — this changes no test command, no dependency, and no job name, so `vault.yml` and `web.yml` behave identically for their lanes.
- contract / URL / header / path: none.

Renovate or Dependabot would keep these pins fresh automatically and is the normal follow-up, but adding a bot is outside the do-not-build fence for 48 hours and is not proposed here. Manual bumps follow the `make help` procedure.

## Blocked on

`nobody`.

## Contract reminder

CI and runbook only. This PR does not invent HTTP routes, touch the span schema, or change deploy behaviour. Deploy is still `main`-only; rollback is still re-running the last green `deploy.yml`. Ingest stays `X-Tenant-Key`; reads stay Cognito JWT.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and .github/workflows/trivy.yml.
Every third-party action in this repo is pinned to a 40-char commit SHA with the
exact semver in a trailing comment. A CI guard in trivy.yml enforces it on every
PR and was verified against six regression cases.
Do not reintroduce a bare @v tag. Do not replace a pin with a TODO.
To bump a pin, follow "Updating a pinned GitHub Action" in make help — resolve
the tag, dereference it if annotated, verify the commit, update the comment too.
Do not merge to main — Trevor merges.
```
