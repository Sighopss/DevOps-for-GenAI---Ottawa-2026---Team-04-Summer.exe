# Handoff — Trevor handbook security controls (#47, #51, #52)

- Date: 2026-08-22
- Human/owner: Trevor
- Branch: `trevor/security/handbook-controls` from `origin/main` at `6e41c7d`
- Issues: closes #47, closes #51, closes #52 after merge
- Apply status: **not applied**; this change adds reviewed configuration and tests only

## Claimed paths

```text
.github/workflows/infra.yml
.github/workflows/sdk.yml
demo-app/README.md
demo-app/src/demo_app/bedrock.py
demo-app/src/demo_app/main.py
demo-app/src/demo_app/rag.py
demo-app/tests/test_agent_controls.py
docs/IAM_DESIGN.md
docs/SCALE.md
infra/README.md
infra/envs/dev.tfvars.example
infra/envs/prod.tfvars.example
infra/lambda.tf
infra/variables.tf
infra/tests/
scripts/check_iam_least_privilege.py
handoffs/trevor-handbook-security-controls.md
```

Collision check before writing: open PR #76 claims `README.md`, `SECURITY.md`, and `docs/ARCHITECTURE.md`; #78 claims `.github/CODEOWNERS`; #88 claims Michael's `web/`, `PRODUCT.md`, and `DESIGN.md`. None overlap these paths. This change does not touch `vault/` or `web/`.

## What shipped

### #47 — agent/tool security

- The live demo call now goes through an immutable `TOOL_REGISTRY` containing exactly `get_doc_metadata`.
- The tool rejects any document whose resolved path leaves `demo-app/corpus/`, including symlink/path traversal outcomes.
- Runtime tests install traps for write, delete, shell, and network APIs and prove the tool reaches none of them.
- Tests prove `run()` has no loop, makes exactly one Converse call, uses a 256-token ceiling, 5-second connect timeout, 30-second read timeout, and one retry.
- `demo-app/README.md` states the allowlist and rationale. Fake Bedrock remains clearly disclosed under P-15.

### #51 — identity and access

- `docs/IAM_DESIGN.md` enumerates ingest, read, GitHub OIDC, API Gateway, CloudFront, and human identities with minimum permissions and explicit exclusions.
- It separates JWT **authentication** from `custom:tenant_id` **authorization**, and ingest-key auth from both.
- `scripts/check_iam_least_privilege.py` fails CI when an authored identity-policy Allow uses `Resource = "*"`, `Action = "*"`, or a service wildcard such as `s3:*`.
- Four regression tests prove bad Allows fail, scoped Allows pass, and defensive wildcard Denies remain valid.
- KMS key-policy wildcards are explicitly excluded because AWS resource-policy semantics require `Resource = "*"` for the attached key; this is not silently waived.

### #52 — abuse, cost, and scale

- `docs/SCALE.md` states traffic, flight-size, AI-call, token, timeout, cost-budget, storage, and 10× assumptions.
- Limit behavior is explicit: API 429, Lambda throttling, timeout, Bedrock failure, and token stop.
- `lambda_reserved_concurrency` is now configurable, with `-1` as the safe default.
- Read-only AWS evidence showed the new account has only **10 total regional concurrent executions**. Reserving 10 on each Lambda would fail, so the 10× runbook correctly requires a quota increase before positive per-function reservations.
- Capacity tests pin throttle 10/20, Lambda 30 seconds/512 MiB, the safe concurrency default, and agent budgets.
- The `< $0.01` per-flight figure is labelled a budget ceiling, not measured billing. The live `cost_usd = 0.0` gap remains disclosed rather than converted into a false claim.

## Handbook evidence

| Handbook gate | Evidence |
|---|---|
| Validate — unsafe-tool and prompt/agent misuse | Immutable one-tool allowlist, side-effect traps, confinement and bounded-call tests |
| Identity & Access | Role/service-identity design note plus wildcard drift gate in `infra.yml` |
| Agent/Tool Security | Exactly one read-only tool; no write/delete/shell/network path |
| Abuse & Cost | API throttle, Lambda/Bedrock timeout, token/iteration/retry ceilings, concurrency quota, limit behavior |
| Governance — monitoring/change | Controls are named constants or Terraform variables and drift is tested in CI |
| Production Readiness — scale | Concrete 10× workload, bottleneck order, quota/config sequence, no unnecessary EKS |
| P-09/P-15 | Tests use `TRACEVAULT_FAKE_BEDROCK=1` and documentation says this is a stub; no live Bedrock claim |

Rubric impact: Security 15%, AI Governance 10%, Reliability & Observability 10%, Engineering & Technical Depth 15%.

## Validation

```text
python scripts/check_iam_least_privilege.py infra/iam.tf infra/oidc.tf infra/iam_team.tf
  ok: 3 Terraform files contain no wildcard Allow grants

python -m unittest discover -s infra/tests -p 'test_*.py' -v
  8 passed

cd demo-app && TRACEVAULT_FAKE_BEDROCK=1 uv run pytest -q
  7 passed

cd sdk && uv run pytest -q
  3 passed

py -m pytest vault -q
  109 passed

terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate -no-color
  Success! The configuration is valid.

git diff --check
  clean

aws lambda get-account-settings --profile tracevault --region us-east-1
  read-only result: regional concurrency quota 10, two functions present
```

No Terraform plan/apply was run from this branch. The existing partially deployed stack and WAF association failure are unchanged.
