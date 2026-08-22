# Handoff — `trevor-team-iam` — `infra/team-iam`

- Date: 2026-08-22
- Human: `Trevor`
- Agent id: `trevor-team-iam`
- Branch: `trevor/infra/team-iam` (from main — #72 merged)
- PR: TBD
- Related: #51 (IAM least-privilege), #36 (real GitHub handles), #48 (deploy)

## Claimed paths (collision)

```
infra/iam_team.tf
handoffs/trevor-infra-team-iam.md
```

## Do not touch

```
vault/ (Alexis)   web/ PRODUCT.md DESIGN.md (Michael)   contracts/ (locked)
```

## Safe to run in parallel with

Anyone not writing `infra/`. Open: #73 (gitignore only, no overlap).

## What I shipped

Operator access for the two other humans, as Terraform rather than console
clicks so it does not drift from state the moment it exists.

Users (`aws_iam_user`, path `/team/`, tagged with the GitHub handle):

| IAM user | Human | GitHub | Lane |
|---|---|---|---|
| `tracevault-alexis` | Alexis Mugisha | `CodingAddict1530` | vault |
| `tracevault-michael` | Michael Nwaeze | `nwaezethedev` | web |

Each gets three attachments:

1. **`ReadOnlyAccess`** (AWS managed) — debug logs, metrics, config anywhere
   without waiting on Trevor.
2. **One lane policy** — write access only where they own code.
   - `tracevault-dev-lane-vault`: update/invoke the two vault Lambdas; write
     the traces table; `PutObject`/`DeleteObject` on the payload bucket
     **restricted to `tenant-a/*` and `tenant-b/*`** (the same prefix fence the
     ingest role gets); `Decrypt`/`GenerateDataKey` on the data KMS key; Logs
     Insights queries on the two vault log groups.
   - `tracevault-dev-lane-web`: `PutObject`/`DeleteObject`/`ListBucket` on the
     web bucket; `CreateInvalidation` on the CloudFront distribution.
3. **`tracevault-dev-team-boundary`** — explicit `Deny`, which beats any Allow
   including a broader policy attached later by mistake:
   - all `s3:*` on the **Terraform state bucket**. `ReadOnlyAccess` would
     otherwise grant `s3:GetObject` on it, and state is the whole account in
     one object — every ARN, every attribute, anything marked sensitive.
   - `secretsmanager:GetSecretValue` and friends — the tenant HMAC keys.
   - all IAM mutation verbs, so neither can escalate themselves.

`var.manage_team_users` (default `true`) exists because IAM is account-global:
if a second env is ever applied into this account it must set this `false` or
the apply collides on user names.

### Access keys are deliberately not in this Terraform

`aws_iam_access_key` puts the secret in state in cleartext. State lives in S3,
and these two users hold `ReadOnlyAccess` — putting their own keys in state is
circular. Keys get minted out of band after apply, one at a time, handed over
once, never written to the repo:

```
aws iam create-access-key --user-name tracevault-alexis  --profile tracevault
aws iam create-access-key --user-name tracevault-michael --profile tracevault
```

Send each secret over a channel that is not this repo and not the PR. If a
secret is ever pasted anywhere shared, delete the key and re-mint — it is two
seconds of work and the only correct response.

## Verification

- `terraform fmt -check -diff` → clean.
- `terraform validate` → **Success! The configuration is valid.**
- `terraform plan` → **not yet run.** The state lock is held (see below).

## Blocked on

**A live state lock.** Lock `f96cff1a-b48c-cf2d-e558-b053e910f265`,
`OperationTypePlan`, held by `DESKTOP-89H9R5F\Topfloorboss` since
2026-08-22T14:26:18Z. Terraform PID **16692** is still alive and idle
(0.7 CPU-seconds over ~9 minutes) — it looks like a plan sitting at an
interactive prompt in another terminal.

I did **not** `force-unlock` and did **not** kill it. Force-unlocking a live
operation is how state gets corrupted, and only the person at that terminal
knows whether it is mid-apply.

Trevor: finish or Ctrl-C that terminal, then the plan and apply here are clean —
every ARN this file references already exists in state.

## Note for the board — the deploy is live

While checking whether these policies had real ARNs to point at, I found the
stack is **applied**: 54 resources in state, and

```
curl https://55qm437628.execute-api.us-east-1.amazonaws.com/health
200 {"ok":true}
```

from the public internet. That is #48's core "Done when" criterion, met.

`README.md` still says *"As of this commit, nothing is deployed"* (line 132) and
still shows **Public URL: TBD** (line 21). Both are now false and should be
updated — that text is exactly what a judge reads first.

CloudFront (`https://d13b678j60bhap.cloudfront.net`) answers **403**, because
the web bucket is empty — `web/` does not exist on any branch yet (#19–#25).
The API is live; the CDN has nothing to serve.