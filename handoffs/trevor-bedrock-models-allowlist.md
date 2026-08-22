# Handoff — trevor-bedrock-models — allowlist

- Date: 2026-08-22
- Human: Trevor
- Agent id: `trevor-bedrock-models`
- Branch: `trevor/fix/bedrock-model-allowlist`
- PR: TBD
- Mission / scope: Pin the agreed Bedrock models (Claude 3.5 Sonnet, Nova Lite, Titan Embed V2) into IAM + demo-app defaults so live RAG is authorised.

## Claimed paths

```
infra/variables.tf
infra/envs/
infra/tests/test_capacity_controls.py
demo-app/src/demo_app/bedrock.py
demo-app/tests/test_agent_controls.py
demo-app/README.md
docs/AI_INVENTORY.md
AI_USAGE.md
GOVERNANCE.md
SECURITY.md
README.md
handoffs/trevor-bedrock-models-allowlist.md
```

## Handbook evidence

- Lifecycle stage: `Validate` / AI supply chain
- P-ids: P-15 (honest live vs stub), inventory closure
- Stub/live: tests still use `TRACEVAULT_FAKE_BEDROCK=1`; live defaults are Nova Lite + Titan Embed V2
- Judge bar: never-kill intact — fake mode unchanged; live path fails closed on unknown converse ids

## What I shipped

- Titan Embed V2 on `bedrock_model_ids` (variables + tfvars examples)
- demo-app defaults + allowlist guard for converse models
- Docs/inventory gap closed

## Blocked on

Next `terraform apply` (and Bedrock console model access for the three ids) before a live call succeeds under the OIDC role.
