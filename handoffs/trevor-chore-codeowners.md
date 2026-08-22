# Handoff — `trevor-codeowners` — `chore/codeowners`

- Date: 2026-08-22
- Human: `Trevor`
- Agent id: `trevor-codeowners`
- Branch: `trevor/chore/codeowners` (from main — #77 merged)
- Closes: #36

## Claimed paths (collision)

```
.github/CODEOWNERS
handoffs/trevor-chore-codeowners.md
```

## What I shipped

Replaced the twelve `@Sighopss` placeholders with the real accounts and gave
each lane its actual owner:

| Path | Owners |
|---|---|
| `/contracts/` | `@Sighopss` `@CodingAddict1530` `@NwaezetheDev` (frozen — all three) |
| `/vault/` | `@CodingAddict1530` `@Sighopss` |
| `/web/`, `/PRODUCT.md`, `/DESIGN.md` | `@NwaezetheDev` `@Sighopss` |
| everything else | `@Sighopss` |

**Verified rather than assumed.** A CODEOWNERS entry naming an account without
push access is silently ignored by GitHub — the rule looks present and routes
nothing, which is exactly the failure #36 exists to prevent. Checked with
`gh api repos/:owner/:repo/collaborators`:

```
Sighopss           push=true  admin=true
CodingAddict1530   push=true
NwaezetheDev       push=true
```

Note the capitalisation is `@NwaezetheDev`, not `nwaezethedev`.

Trevor still merges everything; ownership here routes review requests, it does
not grant merge rights.

## Note for the board

There is a **pending, unaccepted invitation** for `Nappasaurus` (write, sent
2026-08-21). If that is Kim or Jemaelle and they are meant to own a path, the
invite has to be accepted first or their CODEOWNERS line will be inert.

## Blocked on

`nobody`.

## Pickup prompt (paste into the other LLM)

```
Read this handoff and PLAN.md.
Do not edit the claimed paths above.
Do not merge to main — Trevor merges.
```
