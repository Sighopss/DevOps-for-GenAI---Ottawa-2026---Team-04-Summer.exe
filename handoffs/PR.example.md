# Handoff — `<your-name>-<id>` — `<slug>`

> **In-tree template for agents working in this product repo.** The canonical version of this file, plus [`PLAN.md`](https://github.com/Sighopss/TVault-scratchbook-accessible/blob/main/PLAN.md) and [`JUDGE.md`](https://github.com/Sighopss/TVault-scratchbook-accessible/blob/main/JUDGE.md), live in the scratchbook at https://github.com/Sighopss/TVault-scratchbook-accessible and must **not** be duplicated into this repo.

- Date:
- Human: `<Trevor|Alexis|Michael>`
- Agent id: `<your-name>-<id>`
- Branch: `<your-name>/<id>/<slug>`
- PR: `<number or TBD>`
- Mission file: `skills/<your-lane>/agents/<id>.md` (in the scratchbook — not in this repo)

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

Empty = incomplete PR. Copy from PLAN **Rubric 100** / P-ids ([`PLAN.md`](https://github.com/Sighopss/TVault-scratchbook-accessible/blob/main/PLAN.md), section **Handbook (2026)**).

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
Read this handoff, then scratchbook PLAN.md and JUDGE.md
(https://github.com/Sighopss/TVault-scratchbook-accessible).
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
