# Handoff — `<your-name>-<id>` — `<slug>`

> **Handoff template.** Copy this to `handoffs/<your-name>-<id>-<slug>.md` on your branch and paste the same text into the PR body.

- Date:
- Human: `<Trevor|Alexis|Michael>`
- Agent id: `<your-name>-<id>`
- Branch: `<your-name>/<id>/<slug>`
- PR: `<number or TBD>`
- Mission / scope:

## Claimed paths (collision)

If another open PR lists an overlapping path, they must not write. You must not write theirs.

```
<paths you will edit, prefixes ok — e.g. vault/redact/ or sdk/>
```

## Do not touch

```
<PLAN paths that belong to someone else>
```

## Safe to run in parallel with

Agents whose claimed paths do **not** overlap this list. Name them if you know (`trevor-infra` vs `alexis-redact`, not “everyone”).

## Handbook evidence (required — 2026 workbook)

Empty = incomplete PR. Name the lifecycle stage, the handbook P-ids, and the rubric rows this PR moves.

- Lifecycle stage: `<Discover|Design|Build|Validate|Deploy|Operate|Govern>`
- P-ids this PR moves: `<e.g. P-09, P-13>`
- Rubric rows (pts): `<e.g. Security 15, DevOps 10>`
- Tests / attack shown:
- Stub/live (P-15):
- Judge bar (`JUDGE.md`): never-kill still intact / named break + owner:

## What I shipped

- files:
- outputs / env **names** (no secret values):
- tests:

## What I need

- from whom:
- contract / URL / header / path:

## Blocked on

`<other-human | Human | nobody>`

## Contract reminder

`<only the interface you own — not another lane’s internals>`

## Pickup prompt (paste into the other LLM)

```
Read this handoff and the ownership table in README.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
