# Handoffs (per PR)

> **In-tree copy for agents working in this product repo.** The canonical version of this file, plus [`PLAN.md`](https://github.com/Sighopss/TVault-scratchbook-accessible/blob/main/PLAN.md) and [`JUDGE.md`](https://github.com/Sighopss/TVault-scratchbook-accessible/blob/main/JUDGE.md), live in the scratchbook at https://github.com/Sighopss/TVault-scratchbook-accessible and must **not** be duplicated into this repo.

Every feature PR **commits** a handoff file and pastes the same text into the GitHub PR body. Other LLMs load that — they do not wait for chat, and they do not implement your slice.

Local `.agent-leases.json` is **one machine**. Open PRs are **the team**. Both are required.

Do not invent routes. After hour 0, HTTP is `contracts/http.md`.

## Collision check (before any write)

1. Scratchbook [`PLAN.md`](https://github.com/Sighopss/TVault-scratchbook-accessible/blob/main/PLAN.md) write paths for **your** human. If the task is another lane, stop. Also [`JUDGE.md`](https://github.com/Sighopss/TVault-scratchbook-accessible/blob/main/JUDGE.md) — do not break Never-kill. Do not add PLAN/JUDGE to the product repo.
2. Local lease: `.agent-leases.json` (gitignored). Overlap + started < 4h → stop. Do not delete someone else’s lease.
3. **Open PRs** (other machines):

```bash
gh pr list --state open --json number,title,headRefName,url
gh pr view <N>
```

Read **Claimed paths** in each PR body / `handoffs/*.md`. If they overlap **your** write paths → **do not write**. Say you are blocked. Do not “just edit the same file.”

4. Claim: copy [`PR.example.md`](PR.example.md) → `handoffs/<your-name>-<id>-<slug>.md` on **your** branch. Fill **Handbook evidence** (stage, P-ids, rubric, tests, stub/live). Empty evidence = incomplete. Open the PR. **Do not merge** — Trevor merges.

Two agents, two worktrees, two PRs. Trevor merging `main` is the integrate step.

## File per PR

| | |
|---|---|
| Path | `handoffs/<your-name>-<id>-<slug>.md` |
| Shape | [`PR.example.md`](PR.example.md) — fill it; do not leave placeholders |
| Git | **Committed on the feature branch.** Not gitignored. Not only in chat. |
| GitHub | Same content in the PR body (template). |

After merge, the file stays on `main` as history. Do not rewrite another PR’s handoff.

## Pickup (other LLM)

```
Read scratchbook PLAN.md, JUDGE.md, START.md (https://github.com/Sighopss/TVault-scratchbook-accessible),
and handoffs/README.md in this repo.
gh pr list --state open
gh pr view <N>
Use only What I shipped / outputs. Do not edit Claimed paths.
Execute my mission only. Do not merge to main — Trevor merges.
```

If you need another lane changed: fill a handoff, open/update **their** wait is the PR, **stop**. Do not implement their tree.
