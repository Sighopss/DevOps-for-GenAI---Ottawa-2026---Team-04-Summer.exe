# Handoff ? trevor-docs ? ai-usage-balance

- Date: 2026-08-22
- Human: Trevor
- Agent id: `trevor-docs-ai-usage`
- Branch: `trevor/docs/ai-usage-balance`
- PR: TBD
- Mission / scope: Rebalance P-06 `AI_USAGE.md` so disclosure stays honest about Cursor / Claude Code / Codex, but reads as human-led planning and review with AI assisting implementation ? not "AI built everything." Branched from `main` after #93 (Bedrock allowlist) merged so the product-model inventory rows stay intact.

## Claimed paths (collision)

```
AI_USAGE.md
handoffs/trevor-docs-ai-usage-balance.md
```

## Do not touch

```
infra/ demo-app/ docs/AI_INVENTORY.md GOVERNANCE.md SECURITY.md README.md
vault/ web/ sdk/ contracts/ scripts/ .github/ Makefile
PRODUCT.md DESIGN.md
```

## Safe to run in parallel with

Anything that does not edit `AI_USAGE.md` human-usage sections. Product Bedrock inventory rows were already updated by merged #93 and are left unchanged here.

## Handbook evidence (required ? 2026 workbook)

- Lifecycle stage: `Govern`
- P-ids this PR moves: `P-06` (AI transparency ? tone/honesty of human vs tool authorship)
- Rubric rows (pts): `Team & AI-tool 5`
- Tests / attack shown: none ? docs-only reframing; no runtime path changed
- Stub/live (P-15): unchanged; Bedrock inventory rows preserved from #93
- Judge bar (`JUDGE.md`): never-kill intact ? disclosure still names real tools; does not invent models or hide AI use

## What I shipped

- files: `AI_USAGE.md` (human-usage intro/table/"Not used" only), this handoff
- outputs / env **names**: none
- tests: n/a (documentation)

## What I need

- from whom: nobody
- contract / URL / header / path: n/a

## Blocked on

`nobody`

## Contract reminder

Docs-only. Does not change vault/SDK/web contracts or Bedrock runtime ids.
