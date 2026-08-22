# Handoffs (per PR)

> **Process reference for agents working in this repo.** One committed handoff file per PR, plus a collision check before any write.

Every feature PR **commits** a handoff file and pastes the same text into the GitHub PR body. Other LLMs load that — they do not wait for chat, and they do not implement your slice.

Local `.agent-leases.json` is **one machine**. Open PRs are **the team**. Both are required.

Do not invent routes. After hour 0, HTTP is `contracts/http.md`.

## Collision check (before any write)

1. Confirm the task is in **your** lane. `README.md` names who owns which tree. If it is another lane, stop.
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

## Another machine

Before you write: read this file, the ownership table in `README.md`, and open PRs (`gh pr list`). Use only **What I shipped** from the relevant handoff. Trevor merges to `main`.

If you need another lane changed: open or update **their** PR and **stop**. Do not implement their tree.
