# Handoff — `trevor-deploy-pipeline` — `deploy-unblock`

- Date: 2026-08-22
- Human: Trevor
- Agent id: trevor-deploy-pipeline
- Branch: trevor/120/deploy-unblock
- PR: TBD
- Mission / scope: #120 (unblock a green `deploy.yml`), #119 (bake `NEXT_PUBLIC_*` from terraform outputs into web-sync), #49 (rollback + approval-gate rehearsal, one failure demo — **found mostly already done in open PR #130**, see "Correction" section below; this PR's contribution to #49 ended up small).

## Claimed paths (collision)

```
.github/workflows/deploy.yml
Makefile
handoffs/trevor-deploy-pipeline.md
```

## Do not touch

```
infra/          web/          sdk/          demo-app/          vault/
README.md       SECURITY.md   docs/
```

## Safe to run in parallel with

Anyone not editing `.github/workflows/deploy.yml` or `Makefile`. Confirmed clean against the current `origin/main` tip (`5d84e3c`, includes #128 WAF-on-CloudFront and #118 cost_usd) — branched from there, not from a stale base.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: Deploy / Operate
- P-ids this PR moves: deploy reliability, rollback/approval evidence (§2 Deploy gate, §5 Production Readiness)
- Rubric rows (pts): Reliability & Observability 10%, DevOps & Delivery 10%
- Tests / attack shown: reproduced both named `deploy.yml` failures from real `gh run view --log-failed` logs before touching anything (see below); validated the new workflow's job graph and YAML with `act -l` (no execution, no AWS calls); hand-verified the new heredoc backend-generation step produces byte-identical output to `infra/backend.tf.example` with the real bucket; confirmed all 7 terraform outputs (`web_bucket`, `cloudfront_distribution_id`, and the 5 `next_public_*`) resolve against live state via `terraform output -json`. Did **not** run `terraform apply` (blocked for me) and could not do a live end-to-end `deploy.yml` run (push to `main` blocked for me).
- Stub/live (P-15): This PR is CI/YAML + runbook only, no application code. Everything it touches is already live infra (verified against AWS, not docs) — the backend bucket, the DynamoDB lock table, and all 7 terraform outputs it reads all exist for real right now.
- Judge bar (`JUDGE.md`): never-kill list untouched — this PR writes no vault/web/sdk code. It strengthens `/health`'s own delivery path indirectly (a working `deploy.yml` is how `/health` ever gets republished) but does not change the route itself.

## What I found (read the logs before you read my fix)

`gh run list --workflow=deploy.yml` showed 9 straight failures on `main`. Root-caused two distinct failures from real `--log-failed` output, not from assumption:

1. **`hashicorp/setup-terraform` `ECONNRESET`** — transient network flake downloading the Terraform binary on the GH-hosted runner (run `32591471661`, step `Setup Terraform 1.9`). Nothing to do with our code; it just kills the job before `init` ever runs.
2. **`terraform output -raw web_bucket` prints the "No outputs found" warning text**, which then gets fed straight into `aws s3 sync s3://<warning text>` and fails parameter validation (run `32592345836`, step `s3 sync + CloudFront invalidate`). Root cause, confirmed by reading `infra/backend.tf.example` + `infra/.gitignore`: **`deploy.yml` never wrote `infra/backend.tf`.** `backend.tf` is gitignored on purpose (the file itself isn't secret, but nothing forces every clone to keep it in sync), so `terraform init` in CI silently fell back to a **local, empty backend** on the ephemeral runner, every single run. That explains both halves of the bug: `apply-dev` tried to re-create all 66 already-live resources into empty state (I saw the real errors: `BucketAlreadyExists` on both S3 buckets, `AccessDenied` on `iam:CreateRole`/`iam:CreateUser`/`kms:TagResource`/`cognito-idp:CreateUserPool`/CloudFront cache-policy creation — the OIDC role is scoped for **updates to an existing stack**, not for creating one from scratch), and `web-sync`'s `terraform output` had nothing to report because its state was just as empty.
3. **Confirmed but separate, already flagged to me**: `apply-prod` ran the identical `init && apply` with no distinct state key and no `TF_VAR_env`, so a real prod run would have written into **dev's own state** under `var.env` still defaulting to `"dev"`. Never triggered yet (no green run at all), but it was live ammunition.
4. **Also checked and already fixed by someone else**, so I did **not** touch it: `trevor-docs-deploy-truth` (merged) recorded `aws_wafv2_web_acl_association.api` as always-failing (WAFv2 REGIONAL scope doesn't attach to HTTP APIs). By the time I rebased onto the current `main` tip, PR #128 (`alexis/infra/waf-cloudfront`) had already moved the WAF onto CloudFront's own `web_acl_id`, and I confirmed the always-failing resource is gone from `infra/api.tf`. Good — one fewer failure mode than the issue described.

I could not run a fresh `terraform plan` against the very latest state to double-check for other drift: **Trevor's own desktop (`DESKTOP-89H9R5F\Topfloorboss`) held the real S3/DynamoDB state lock while I was working** (confirmed by the lock error itself, not assumed — same signature Alexis's runbook warns about). I did not force past it. An earlier plan I ran (before rebasing onto your latest infra changes) showed mostly benign in-place diffs (Lambda source hash noise, an S3 bucket-policy key-order diff, an IAM policy-boundary attach for Alexis) and nothing alarming, but treat that as stale — re-plan yourself once your local run is done.

## What I shipped

- `.github/workflows/deploy.yml`:
  - **Backend fix (closes #120's root cause).** Every job that runs terraform (`apply-dev`, `apply-prod`, `web-sync`) now writes `infra/backend.tf` from known values right before `terraform init`: bucket `tracevault-tfstate-887991000498`, table `tracevault-tf-locks`, region `us-east-1` — same values as `infra/backend.tf.example`, just filled in. Nothing secret is added; the bucket name is already visible throughout `infra/iam_team.tf`.
  - **dev/prod state isolation (closes the risk you flagged).** `apply-dev` uses `TF_VAR_env=dev` + key `dev/terraform.tfstate`; `apply-prod` uses `TF_VAR_env=prod` + key `prod/terraform.tfstate`. A prod run can no longer read or write dev's state, and would build under `tracevault-prod-*` names instead of colliding with `tracevault-dev-*`.
  - **`ECONNRESET` retry.** Each `hashicorp/setup-terraform` step gets one retry (15s wait, then re-run the same pinned action) instead of failing the whole job on one flaky download. No new third-party action added — reused the SHA already pinned in this file.
  - **`web-sync` no longer trusts an empty `terraform output`.** It now reads `terraform output -json`, and if `web_bucket` or `cloudfront_distribution_id` come back empty it fails loudly (`::error::` + `exit 1`) instead of handing `aws s3 sync` a garbage bucket name. This is the exact bug from #120, closed at the source rather than patched around.
  - **NEXT_PUBLIC_* baked from terraform outputs (closes #119).** The same output-read step also pulls `next_public_api_url`, `next_public_cognito_region`, `next_public_cognito_user_pool_id`, `next_public_cognito_client_id`, `next_public_cognito_domain` and exports them to `$GITHUB_ENV` **before** `pnpm build` runs (Next.js inlines `NEXT_PUBLIC_*` at build time, not at runtime — the reorder matters). If any of the five come back empty, it logs an explicit `::warning::` and builds fixture-only rather than silently shipping a half-live build — the Day-1 fixture path stays intact and honestly labelled, per the issue's own done-when.
  - Nothing hardcoded: every one of the 5 values and the two bucket/distribution values comes from `terraform output`, never from a literal.
- `Makefile`:
  - Added a **"Deploy state"** section explaining why `infra/backend.tf` is gitignored and what CI now does about it, so the next person reading `make help` doesn't have to reverse-engineer it from a failed run again.
  - Added the command-level mechanics of a rollback (exact `gh run list` / `gh run rerun` / `gh run watch`, what "confirmed recovery" means concretely) under the existing "Rollback" heading. **I initially wrote a much bigger rewrite here, including a full "Failure demo" section — see correction below, I walked most of that back.**
  - Updated the **human checklist** against live AWS/GitHub state instead of leaving stale claims: main branch protection, the `dev`/`prod` GitHub Environments, and the `AWS_ROLE_ARN` secret are now marked `[x]` because I checked `gh api repos/:owner/:repo/branches/main/protection` and `gh api repos/:owner/:repo/environments` and `gh secret list` directly — **all three already exist**, which contradicts what I was told going in ("no environments configured"). See "What Trevor asked me to flag" below.

## Correction — I stepped on PR #130, caught it before it mattered

Partway through I found **PR #130** (`trevor/ops/deploy-observe-inventory`, open, not merged) already does the real, tested version of #49's rollback + failure-demo work: `docs/DEPLOY_GATE.md` (a recorded drill log), `scripts/demo_ingest_down.sh` (an actual dedicated script, its test-plan checkbox already run: "writes `sdk/.last-flight.json`, exit 0"), and confirms the same `prod` reviewer I found independently. It also touches `Makefile` in the same "Rollback" section I was editing.

My first draft of this PR had invented its own competing "Failure demo" section (pointing at `scripts/demo_pii_flight.sh` with a dead ingest URL — untested by me, never actually run) and a full rollback-drill rewrite. That would have both duplicated **and conflicted** with #130's more authoritative, already-executed version. I removed the invented failure-demo section and trimmed the rollback section down to only the command-level mechanics (the exact `gh run rerun`/`gh run watch` commands), which #130's version doesn't have and isn't likely to conflict on. Whichever of these two PRs merges second should take a quick look at the other's `Makefile` hunk before resolving — they're now adjacent, not identical, but not proven conflict-free either.

**Net effect on #49**: this PR no longer claims to move #49 forward beyond "the approval gate is real, verified live" (see below) and the small command-mechanics addition. PR #130 is the one actually closing it.
- outputs / env **names** (no secret values): `AWS_ROLE_ARN` (secret, already set), `TF_VAR_TENANT_A_PASSWORD` / `TF_VAR_TENANT_B_PASSWORD` (secrets, **not** set — CI placeholder covers it, harmless since Cognito passwords are `lifecycle.ignore_changes`d), `TF_STATE_BUCKET` / `TF_STATE_TABLE` (new job-level env in `deploy.yml`, not secret), the 5 `NEXT_PUBLIC_*` names (unchanged, now sourced live).
- tests: `act -l -W .github/workflows/deploy.yml` (job graph + YAML parse, no execution); manually replayed the backend-generation heredoc through bash and diffed it against `infra/backend.tf.example`; manually replayed the `terraform output -json` → field-extraction logic against real live output (all 7 fields present and correct); rendered the whole `make help` recipe through `sh` (no `make` binary on this box, same workaround the last CI handoff used) and read the output for garbled quoting — clean.

## What Trevor asked me to flag, but I found already done — verify and correct me if I'm wrong

Going in, I was told: no GitHub environments exist, and to tell you to set `AWS_ROLE_ARN` and create environment protection. Live `gh api` calls say otherwise, timestamped **today**:
- `AWS_ROLE_ARN` secret: already set (`2026-08-22T16:56:23Z`).
- GitHub Environment `dev`: exists, no protection rules (fine — no approval friction for the fast lane).
- GitHub Environment `prod`: exists, **required reviewer = Sighopss**, plus a branch-policy restricting deploys to protected branches.
- `main` branch protection: PR required, 1 approval, no force-push.

So the approval-gate half of #49 already looks real on the GitHub side. What is **not** done, and is not something I can do:
- **No `deploy.yml` run on `main` has ever gone green.** Even with this PR's fixes, someone has to actually push/merge to `main` and watch it — I can't push to `main` or merge.
- **The rollback drill and failure demo are PR #130's, not mine** — see correction above. This PR only adds the command-level `gh run rerun`/`gh run watch` mechanics to `make help`; #130 has the actual recorded drill and a real, already-run failure-demo script.
- **`apply-prod` has never actually run.** With this PR it is now *safe* to run (separate state, separate resource names) but it has never been tested end-to-end and would provision a **second, independent, full stack** (new Cognito pool, new CloudFront distribution, new S3 buckets, ~66 more resources) under `tracevault-prod-*` — real cost, several minutes, first time ever. I did not decide this for you: if "prod" for this hackathon is actually supposed to mean "the same dev URL, promoted" rather than a second live stack, `apply-prod` should probably be turned into a no-op or removed instead of exercised. Flagging, not deciding.
- I noticed (but left alone, not in my fence, not referenced by any workflow) that GitHub repo **variables** `AWS_WEB_BUCKET`, `AWS_CLOUDFRONT_DISTRIBUTION_ID`, and all 5 `NEXT_PUBLIC_*` already exist as manually-set repo vars, matching today's live terraform outputs exactly. They're unused by any workflow right now. I deliberately did **not** wire `web-sync` to read them instead of `terraform output` — that would reintroduce exactly the hardcoding #119 says not to do (they'd silently go stale on the next `terraform apply`, e.g. if Cognito is ever recreated). Worth deleting them once you're happy this PR's live-output path works, so nobody mistakes them for the source of truth.

## Blocked on

Trevor: merge this PR, then push/merge something small to `main` (or manually trigger) to get the **first real green `deploy.yml` run** — watch it with `gh run watch`, and if `apply-dev` fails on something new, that failure is now easy to read because outputs are no longer poisoned by empty state. Reconcile this PR's small `Makefile` "Rollback" hunk against #130's before or after merging either — same section, not identical, not proven conflict-free. Decide `apply-prod`'s fate (safe-and-idle vs. actually provision a second stack) — not mine to call.

## Contract reminder

This PR owns `deploy.yml` and the `Makefile` runbook only. It does not change what gets deployed (`infra/`, `web/`, `sdk/`, `vault/` are all untouched) — only how reliably the existing, already-designed pipeline gets from a green PR to a live URL, and what a person does when it isn't.
