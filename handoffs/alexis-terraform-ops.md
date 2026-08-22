# Handoff — `alexis-tfops` — `waf-cloudfront`

- Date: 2026-08-22
- Human: `Alexis`
- Agent id: `alexis-tfops`
- Branch: `alexis/infra/waf-cloudfront`
- Closes: #100. Advances #116 (delegated Terraform ops).

## Claimed paths

```
infra/api.tf
infra/cloudfront.tf
handoffs/alexis-terraform-ops.md
```

`infra/backend.tf` and `infra/tfplan.bin` were created locally and are gitignored — verified with `git check-ignore` before committing. Nothing secret is in this PR.

## Do not touch

```
vault/ (mine, not this PR)   web/ (Michael)   sdk/ demo-app/ scripts/ .github/ (Trevor)
```

## Terraform ops record (#116)

- **Init against remote state: works from this machine.** No lock thrash. Before starting I confirmed no lock was held — the only row in `tracevault-tf-locks` is the `-md5` digest, not an active lock, so there was no collision with `DESKTOP-89H9R5F\Topfloorboss`.
- **`terraform apply` 2026-08-22 19:02:53Z → 19:03:34Z** (41s). `Apply complete! Resources: 1 added, 1 changed, 1 destroyed.` Lock released cleanly on exit.
- **A full `terraform plan` is not possible under my boundary** and will not be. Terraform refreshes every resource, and `tracevault-dev-alexis-boundary` explicitly denies `iam:GetRole` / `GetUser` / `GetPolicy`, so a full plan fails on `aws_iam_role.ingest`, `.read`, `.gha_oidc`, `aws_iam_user.team[*]`, `aws_iam_policy.web_lane`, `.team_boundary`. Targeted plan/apply works and is what I used — this is the expected shape of the delegation, not a misconfiguration.
- **Tenant passwords** were supplied as `TF_VAR_*` from the environment for the plan/apply only. No secret values were read from or written to Secrets Manager, and no access keys were minted.

### Drift reconciled

The CSP drift was **not** safe to apply as written. Live had `script-src 'self' 'unsafe-inline'`; the config had `script-src 'self'`. Applying the config would have *stripped* `'unsafe-inline'` and very likely broken the Explorer, which is a Next.js static export that emits an inline bootstrap script. Config now matches live.

A second, unlisted drift on the same resource: live has an `xss_protection` block that the config did not declare, so Terraform wanted to delete it. Declared it so the resource is clean. Note it is a legacy header — the browser XSS auditor it controls has been removed from current browsers, so the CSP above is the control that actually applies. Dropping it is a reasonable future call for the infra owner; I did not make that call inside a delegated apply.

After both edits: `terraform plan -target=aws_cloudfront_response_headers_policy.web` → **`No changes. Your infrastructure matches the configuration.`**

## What I shipped (#100)

Two things were wrong, and the second is why previous attempts failed:

1. **The ACL was `scope = "REGIONAL"`.** CloudFront requires a `CLOUDFRONT`-scoped ACL, and `scope` is immutable — so this could not be re-pointed, it had to be **replaced**. Zero risk: the old ACL was attached to nothing and filtered no traffic.
2. **`aws_wafv2_web_acl_association` does not work for CloudFront at all.** That resource only supports REGIONAL targets, which is exactly why it failed on every apply. CloudFront takes `web_acl_id` on the distribution instead (the **ARN** for WAFv2; the ID form is WAF Classic). Removed the association, added `web_acl_id`.

The resource address stays `aws_wafv2_web_acl.api` to avoid a state move; the ACL's own name is corrected to `tracevault-dev-cdn`.

### Verified after apply

| Check | Result |
|---|---|
| CLOUDFRONT-scope ACL exists | `tracevault-dev-cdn` / `…:global/webacl/tracevault-dev-cdn/cd073d62-…` |
| Old REGIONAL ACL | gone |
| Distribution `WebACLId` | matches the ACL ARN |
| Distribution status | `Deployed` |
| ACL contents | `DefaultAction: Allow`, `AWSManagedRulesCommonRuleSet` at priority 1 |
| Explorer `/` and `/explorer` | **200** — not broken |
| API `/health` | **200** — unaffected (WAF is on CloudFront, not the API) |

### Not yet verified — WAF evaluation

**The association is in place and config-verified, but I have not yet observed WAF evaluating traffic.** ~4 minutes after apply: XSS and SQLi payloads against the edge still return `200`, `get-sampled-requests` returns 0, and `AWS/WAFV2` `AllowedRequests` has no datapoints. That is consistent with CloudFront edge propagation of a WAF association (usually 10–20 minutes) plus CloudWatch metric lag, but **I am not claiming it works until I see it**. Re-check command:

```bash
aws wafv2 get-sampled-requests --scope CLOUDFRONT --region us-east-1 \
  --web-acl-arn arn:aws:wafv2:us-east-1:887991000498:global/webacl/tracevault-dev-cdn/cd073d62-abe4-4398-8a3b-85f35c211e2d \
  --rule-metric-name ALL --max-items 10 \
  --time-window StartTime=<iso>,EndTime=<iso>
```

If it is still not evaluating well after propagation, the next thing I would check is whether the managed rule group needs a higher-priority explicit rule to demonstrate a block, since `SizeRestrictions_BODY` and `NoUserAgent_HEADER` are already overridden to `count`.

One naming nit left deliberately: the ACL's `visibility_config.metric_name` is still `tracevault-dev-api`, so CloudWatch dimensions use that name. I did not change it because it would churn the metric series; rename it if you would rather the metrics read `-cdn`.

## Residual drift / still Trevor

- **#101** custom domain + ACM + real TLS 1.2 floor — needs DNS Trevor owns. Untouched.
- Anything requiring IAM mutation — my boundary denies it by design.
- `SECURITY.md` / `docs/RED_TEAM.md` perimeter rows still say "WAF filters nothing". I will update that wording once evaluation is observed, so the docs never run ahead of the evidence.

## Blocked on

`nobody`. Trevor merges. Lock is released — his laptop is free to run Terraform again.
