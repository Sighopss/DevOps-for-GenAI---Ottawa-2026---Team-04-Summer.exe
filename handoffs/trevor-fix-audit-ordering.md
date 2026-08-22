# Handoff — `trevor-audit-order` — `fix/audit-ordering`

- Date: 2026-08-22
- Human: `Trevor`
- Agent id: `trevor-audit-order`
- Branch: `trevor/fix/audit-ordering` (from main — #67 merged)
- PR: TBD
- Mission: repo-health sweep, not a board issue. Two defects found reviewing main.

## Claimed paths (collision)

```
vault/audit/log.py
vault/store/keys.py          (docstring + one param rename)
vault/tests/audit/test_list_events.py
infra/.gitignore
handoffs/trevor-fix-audit-ordering.md
```

## Do not touch

```
sdk/ demo-app/ scripts/ .github/ Makefile   (other Trevor lanes)
web/ PRODUCT.md DESIGN.md                   (Michael)
contracts/                                  (locked — unchanged by this PR)
```

## Safe to run in parallel with

Anyone not writing `vault/audit/` or `infra/.gitignore`. No open PRs overlap.

## What I shipped

**1. `list_events` ordering was not deterministic (real defect, invisible to CI).**

`vault/tests/audit/test_list_events.py::test_lists_own_events_oldest_first` fails
intermittently on Windows — 2 of 10 runs before this change:

```
assert ['user-2', 'user-1'] == ['user-1', 'user-2']
```

Root cause: `record()` built the sort key as `a#{trace}#{ts}#{uuid4hex}`, where
`ts` comes from `datetime.now()`. That clock is microsecond-resolution at best,
and on Windows it repeats the same value for ~15ms — measured here at **199 of
200 back-to-back calls identical**. When two events share a `ts`, the sort key
tie-breaks on the *random* uuid, so ordering is a coin flip; `sorted(..., key=ts)`
is stable and just preserves whatever the query returned.

This is not only a test problem. `GET /v1/traces/{trace_id}/audit` records a row
and then lists — the two writes that land closest together in the whole system
are the ones this ordering guarantee covers, and the docstring promises
"oldest first".

Linux CI has true microsecond resolution, so it passes there essentially always.
**CI cannot see this class of bug.**

Fix: one clock read per `record()` produces both the ISO `ts` (format unchanged)
and a nanosecond sequence that is strictly increasing within the process. Sort
key is now `a#{trace}#{ts}#{seq:019d}#{entropy}`, and `list_events` orders on the
sort key — a total order — rather than on `ts`.

- `ts` attribute, `AuditEvent`, and `to_dict()` are byte-identical to before.
  **No contract change**; `contracts/http.md` untouched.
- Sort-key prefix `a#{trace_id}#` is unchanged, so the `begins_with` query and
  every tenant/trace isolation test are unaffected.
- No stored data to migrate — nothing is deployed (#48).
- Cross-process ties (two Lambda instances in one nanosecond) still break on the
  entropy suffix. That is unorderable in principle; uniqueness is what matters
  there and it is preserved.

New regression test `test_same_microsecond_events_keep_write_order` pins both the
clock and the entropy so the failure is deterministic instead of a coin flip.
Verified it **fails on main's code** at the ordering assertion and passes here.

**2. `infra/backend.tf` was untracked but not ignored.**

It holds the real state bucket and AWS account id, and `backend.tf.example` says
in its own header not to commit it — but no `.gitignore` covered it, so
`git check-ignore` returned nothing and one `git add -A` would have committed it.
gitleaks does not flag a bare account id. Added `backend.tf` to `infra/.gitignore`
with `!backend.tf.example` so the template stays tracked. Both verified with
`git check-ignore -v`.

## Verification

- `python -m pytest vault` → **109 passed** (108 before: 107 passing + 1 flaky, plus the new test).
- Audit suite run **30x consecutively → 0 failures** (was failing ~20% of runs).
- `bandit -r vault -x "*/tests/*"` → 0 issues.
- `git check-ignore -v infra/backend.tf` → matches; `backend.tf.example` not ignored.

## What I need

- from whom: **Trevor** — merge. Nothing else blocks on this.

## Blocked on

`nobody`.

## Note for the board

Neither of these is a board issue. Worth knowing while #18/#54 (adversarial and
red-team evidence) are still open: the ordering bug is the kind that only shows
up off the CI platform, so "green on Actions" is not by itself evidence for the
audit trail's ordering guarantee. This PR gives that guarantee a test that holds
on any platform.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Continue your own mission using What I shipped.
Do not merge to main — Trevor merges.
```
