# Handoff — `trevor-tfplan-ignore` — `fix/ignore-tfplan`

- Date: 2026-08-22
- Human: `Trevor`
- Agent id: `trevor-tfplan-ignore`
- Branch: `trevor/fix/ignore-tfplan` (from main — #72 merged)
- PR: TBD
- Mission: follow-up to #72. Same defect class, worse payload.

## Claimed paths (collision)

```
.gitignore
infra/.gitignore
handoffs/trevor-fix-ignore-tfplan.md
```

## Do not touch

```
vault/ (Alexis)   web/ PRODUCT.md DESIGN.md (Michael)   contracts/ (locked)
```

## Safe to run in parallel with

Anyone — gitignore only, no code. No open PRs.

## What I shipped

`infra/tfplan` appeared in the working tree right after #72 merged, untracked
and unignored. It is a saved plan (`terraform plan -out=tfplan`), which is a zip
containing `tfconfig`, `tfplan`, **`tfstate`** and **`tfstate-prev`**. Confirmed
by extracting it: it carries the AWS account id `887991000498`, `arn:aws:iam::`
ARNs, and the state bucket name.

This is the #72 hole again with a much larger payload — a plan archive is
effectively state at rest. `*.tfstate` and `*.tfstate.*` do not match a file
named `tfplan`, so nothing covered it, and gitleaks does not reliably read
inside a binary zip.

Neither `make plan` nor `.github/workflows/infra.yml` produces it — both run
bare `terraform plan` with no `-out`. It came from a manual run, which means it
will keep reappearing while #48 (deploy) is being worked. Ignoring it now, not
after.

Added to **both** `.gitignore` and `infra/.gitignore`:

```
tfplan
tfplan.*
*.tfplan
*.tfplan.json
```

`*.tfplan.json` covers `terraform show -json tfplan > out.tfplan.json`, which is
plaintext state and the easier one to leak.

## Verification

- `git check-ignore -q` → ignored: `infra/tfplan`, `infra/tfplan.json`,
  `infra/dev.tfplan`, `infra/my.tfplan.json`, `tfplan`.
- Not ignored (correct): `infra/backend.tf.example`, `infra/api.tf`, `infra/envs`.
- No code touched; vault suite unaffected (109 passing on main).

## What I need

- from whom: **Trevor** — merge. `infra/tfplan` is still on your disk; it is safe
  to delete once the apply it was built for has run.

## Blocked on

`nobody`.

## Note for the board

Two files in two days were one `git add -A` from publishing account
infrastructure (#72's `backend.tf`, now `tfplan`). Worth a line in the #54
red-team writeup: the repo's secret scanning is gitleaks-only, which is
pattern-based on text and does not open archives. An `infra/`-scoped
`git status` check before commit, or a pre-commit hook, would catch the next one
by shape rather than by luck.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
