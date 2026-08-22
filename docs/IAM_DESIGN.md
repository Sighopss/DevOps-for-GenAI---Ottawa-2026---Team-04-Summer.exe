# IAM design and authorization boundaries

This is the judge evidence for handbook §3 **Identity & Access**. TraceVault separates service identity, human access, authentication, and tenant authorization. The automated source guard is `scripts/check_iam_least_privilege.py`; `.github/workflows/infra.yml` runs it on every relevant pull request.

## Service identities

| Identity | Assumed by | Minimum capability | Explicitly absent |
|---|---|---|---|
| `tracevault-*-vault-ingest` | `vault-ingest` Lambda only | Write masked payloads under the two tenant S3 prefixes; put/update/query this DynamoDB table; use this KMS key; read the two ingest secrets; write its logs | No S3 reads/deletes, no IAM, no Bedrock, no other buckets/tables/secrets |
| `tracevault-*-vault-read` | `vault-read` Lambda only | Read payloads under the two tenant prefixes; get/query the table and append an audit row; decrypt with this KMS key; write its logs | No payload writes/deletes, no secret reads, no IAM, no Bedrock |
| `tracevault-*-gha-oidc` | GitHub Actions for this repository, using short-lived OIDC credentials | Update/invoke the two Lambdas; publish/sync this stack's S3 objects; update this table; pass only the two Lambda roles to Lambda; invalidate this CloudFront distribution; use this KMS key and tenant secrets; invoke the allowlisted Bedrock models | No static access key, no arbitrary `PassRole`, no other repository in the trust policy, no wildcard resource grant |
| API Gateway | AWS service | Invoke only the mapped Lambda routes | Cannot assume either Lambda role or read storage directly |
| CloudFront OAC | CloudFront service | Read only the web bucket, conditioned on this distribution ARN | No payload-bucket access |

The OIDC role is an application deployment identity, not an account administrator. Initial account bootstrap and Terraform changes that create unsupported resource types remain an explicit Trevor-operated action. The current `deploy.yml` runs Terraform, but an infrastructure change outside the role's allowlist will fail closed rather than silently gaining privilege.

## Human identities

Humans never share Trevor's bootstrap credential. `infra/iam_team.tf` creates separate `tracevault-alexis` and `tracevault-michael` users, does not create access keys in Terraform state, and gives each person read-only troubleshooting plus lane-specific writes. Alexis can update the two vault Lambdas and tenant-scoped vault data; Michael can publish the web bucket and invalidate this CloudFront distribution. A shared explicit-deny policy blocks Terraform-state reads, tenant-secret mutation/read, and IAM mutation even if broader access is attached later. Trevor owns infrastructure and merges.

For a longer-lived environment, migrate these humans to IAM Identity Center with MFA. The IAM users are a time-boxed hackathon compromise, not the target enterprise access model.

## Authentication is not authorization

1. API Gateway's Cognito JWT authorizer validates issuer, audience, signature, and expiry. That establishes **who** presented a valid product identity.
2. `vault-read` then compares the ID token's `custom:tenant_id` with the flight owner. That establishes **what that identity may read**. A valid JWT alone does not confer cross-tenant access.
3. Ingest does not accept a Cognito JWT. It uses a separate per-tenant `X-Tenant-Key` from Secrets Manager and scopes writes to that tenant. An ingest key is never a user token.
4. Cross-tenant detail reads return the contracted **403**, not 404. No admin bypass is designed.

## Drift test and review rule

The CI guard examines the three authored identity-policy files (`iam.tf`, `oidc.tf`, and `iam_team.tf`). It rejects any **Allow** containing `Resource = "*"`, `Action = "*"`, or a service-wide action such as `s3:*`. Explicit Deny statements may use wildcards because they reduce privilege. KMS key policies are resource policies attached to one key and require `Resource = "*"` under AWS policy semantics, so they are reviewed separately rather than misclassified by this identity-policy gate. AWS-managed `ReadOnlyAccess` is also outside source parsing; the shared deny policy compensates for its broad read scope over state and secrets.

The guard complements, rather than replaces, review of tenant-prefix expressions, trust-policy subjects, and action semantics. Any new role must be added to the table above and must pass `python scripts/check_iam_least_privilege.py infra/iam.tf infra/oidc.tf infra/iam_team.tf`.
