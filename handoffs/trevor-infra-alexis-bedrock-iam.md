# Handoff — `trevor-infra` — `alexis-bedrock-iam`

- Date: 2026-08-22
- Human: Trevor
- Agent id: `trevor-infra`
- Branch: `trevor/infra/alexis-bedrock-iam`
- PR: TBD
- Mission / scope: Add scoped Bedrock invoke (+ GetFoundationModel) to Alexis vault-lane IAM; hand live Nova/Titan verify + Claude retarget follow-up to Alexis (#104).

## Claimed paths (collision)

```
infra/iam_team.tf
docs/IAM_DESIGN.md
handoffs/trevor-infra-alexis-bedrock-iam.md
```

## Do not touch

```
vault/
sdk/
web/
infra/oidc.tf
infra/iam.tf
```

## Safe to run in parallel with

`alexis/docs/security-honesty` (#103) — docs/red-team only; no IAM overlap.

## Handbook evidence (required — 2026 workbook)

- Lifecycle stage: Deploy / Validate
- P-ids this PR moves: P-09 (least privilege), P-04 (working system — live Bedrock verify path)
- Rubric rows (pts): Security (IAM least privilege), DevOps (operator access without shared admin)
- Tests / attack shown: `python scripts/check_iam_least_privilege.py infra/iam.tf infra/oidc.tf infra/iam_team.tf`; no `bedrock:*` / `Resource "*"` on Allow
- Stub/live (P-15): IAM source change; live policy version applied via CLI if full terraform apply still blocked (#48)
- Judge bar (`JUDGE.md`): never-kill intact — deny boundary unchanged; no secrets in git

## What I shipped

- files: `infra/iam_team.tf` (BedrockInvokeScoped + BedrockGetFoundationModel on Alexis vault lane), `docs/IAM_DESIGN.md`, this handoff
- outputs / env **names** (no secret values): uses existing `bedrock_model_ids` / `local.bedrock_model_arns`
- tests: IAM least-privilege guard

## What I need

- from whom: Alexis (`CodingAddict1530`) — issue #104 smoke Nova/Titan; Claude EOL retarget + Anthropic form follow-up (ping Trevor if account form blocked)
- contract / URL / header / path: models already live — `amazon.nova-lite-v1:0`, `amazon.titan-embed-text-v2:0`; Claude 3.5 Sonnet id EOL

## Blocked on

Full `terraform apply` remains #48. Prefer merge this PR then `aws iam create-policy-version` on `tracevault-dev-lane-vault` so Alexis can smoke without waiting for apply.

## Contract reminder

Alexis invoke is scoped to the same model ARNs as OIDC — not account Bedrock admin.
