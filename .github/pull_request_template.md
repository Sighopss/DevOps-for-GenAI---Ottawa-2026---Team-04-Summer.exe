## Handoff (required)

Every PR needs a committed file `handoffs/<your-name>-<id>-<slug>.md` (copy `handoffs/PR.example.md`) **and** the same text below. Other LLMs use this to work in parallel. Trevor merges; you do not.

**Handoff path:** `handoffs/<your-name>-<id>-<slug>.md`

Paste that file’s body under this heading (required for other LLMs):

```
```

## Handbook (required)

- [ ] Handoff has **Handbook evidence** (stage, P-ids, rubric rows, tests, stub vs live)
- [ ] I did not skip the PLAN Cycle gate (no Build before hour 0 Design)

## Collision

- [ ] I listed **Claimed paths** (prefixes I will write)
- [ ] I ran `gh pr list --state open` and no open PR claims an overlapping path
- [ ] Local `.agent-leases.json` leased my id only
- [ ] I did not edit another human’s tree (`sdk/` / `vault/` / `web/` per PLAN.md)

## Summary

-

## Test plan

- [ ]
