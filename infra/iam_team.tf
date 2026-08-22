# Human operator access for the two other humans on the team.
#
# Shape: AWS managed ReadOnlyAccess for debugging anywhere in the account,
# plus one customer-managed write policy scoped to the lane that person
# actually owns (PLAN.md: Alexis vault/, Michael web/), plus a shared deny
# boundary that holds even if a broader policy is attached later.
#
# Access keys are deliberately NOT created here. aws_iam_access_key stores
# the secret in Terraform state in cleartext; state lives in S3 and anyone
# with ReadOnlyAccess -- including these two users -- can read an S3 object.
# Keys are minted out of band with `aws iam create-access-key` and handed
# over once. See handoffs/trevor-infra-team-iam.md.

variable "manage_team_users" {
  type        = bool
  description = <<-EOT
    Create the per-human IAM users. IAM is account-global, so if a second
    env (prod) is ever applied into this same account it must set this to
    false or the apply collides on the user names.
  EOT
  default     = true
}

locals {
  team = {
    alexis = {
      github = "CodingAddict1530"
      lane   = "vault"
    }
    michael = {
      github = "nwaezethedev"
      lane   = "web"
    }
  }

  team_users = var.manage_team_users ? local.team : {}

  # backend.tf is gitignored, so the state bucket is derived rather than
  # hardcoded -- same expression the bootstrap in infra/README.md uses.
  tfstate_bucket_arn = "arn:${local.partition}:s3:::${var.project}-tfstate-${local.account_id}"
}

resource "aws_iam_user" "team" {
  for_each = local.team_users

  name = "${var.project}-${each.key}"
  path = "/team/"

  tags = {
    GitHub = each.value.github
    Lane   = each.value.lane
  }
}

# Read anything, so they can debug logs, metrics and config without waiting
# on Trevor. Note this does include s3:GetObject on the payload bucket --
# that data is redacted at ingest (vault/redact, fail-closed), which is the
# control that makes this acceptable rather than the IAM boundary.
resource "aws_iam_user_policy_attachment" "team_readonly" {
  for_each = local.team_users

  user       = aws_iam_user.team[each.key].name
  policy_arn = "arn:${local.partition}:iam::aws:policy/ReadOnlyAccess"
}

# --- Alexis: vault lane -----------------------------------------------------

data "aws_iam_policy_document" "vault_lane" {
  statement {
    sid    = "DeployVaultLambdas"
    effect = "Allow"
    actions = [
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:PublishVersion",
      "lambda:InvokeFunction",
    ]
    resources = [
      aws_lambda_function.ingest.arn,
      aws_lambda_function.read.arn,
    ]
  }

  statement {
    sid    = "TracesTableWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [aws_dynamodb_table.traces.arn]
  }

  # Tenant prefixes only -- the same fence the ingest role gets, so a human
  # cannot write outside the layout IAM enforces for the Lambdas.
  statement {
    sid    = "PayloadObjectsTenantPrefix"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      for tenant in local.tenants : "${aws_s3_bucket.payload.arn}/${tenant}/*"
    ]
  }

  statement {
    sid    = "DataKeyUse"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
    ]
    resources = [aws_kms_key.data.arn]
  }

  # ReadOnlyAccess covers GetLogEvents but not Insights queries, which is
  # what actually gets used when chasing a failed flight.
  statement {
    sid    = "LogInsights"
    effect = "Allow"
    actions = [
      "logs:StartQuery",
      "logs:StopQuery",
      "logs:GetQueryResults",
      "logs:FilterLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.ingest.arn}:*",
      "${aws_cloudwatch_log_group.read.arn}:*",
    ]
  }

  # Same scoped invoke allowlist as the GHA OIDC role (local.bedrock_model_arns).
  # Lets Alexis smoke live demo-app Bedrock without sharing Trevor's admin key.
  # PutFoundationModelEntitlement is retired (auto model access); do not grant *.
  # ListFoundationModels stays on ReadOnlyAccess (AWS list APIs require Resource *).
  statement {
    sid    = "BedrockInvokeScoped"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = local.bedrock_model_arns
  }

  statement {
    sid    = "BedrockGetFoundationModel"
    effect = "Allow"
    actions = [
      "bedrock:GetFoundationModel",
    ]
    resources = [
      for id in var.bedrock_model_ids :
      "arn:${local.partition}:bedrock:${var.aws_region}::foundation-model/${id}"
    ]
  }
}

resource "aws_iam_policy" "vault_lane" {
  name        = "${local.name}-lane-vault"
  description = "Write access to the vault lane (Alexis)."
  policy      = data.aws_iam_policy_document.vault_lane.json
}

resource "aws_iam_user_policy_attachment" "alexis_lane" {
  count = var.manage_team_users ? 1 : 0

  user       = aws_iam_user.team["alexis"].name
  policy_arn = aws_iam_policy.vault_lane.arn
}

# --- Michael: web lane ------------------------------------------------------

data "aws_iam_policy_document" "web_lane" {
  statement {
    sid    = "PublishWebBundle"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.web.arn}/*"]
  }

  statement {
    sid       = "ListWebBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.web.arn]
  }

  statement {
    sid    = "InvalidateCdn"
    effect = "Allow"
    actions = [
      "cloudfront:CreateInvalidation",
      "cloudfront:GetInvalidation",
      "cloudfront:ListInvalidations",
    ]
    resources = [aws_cloudfront_distribution.web.arn]
  }
}

resource "aws_iam_policy" "web_lane" {
  name        = "${local.name}-lane-web"
  description = "Write access to the web lane (Michael)."
  policy      = data.aws_iam_policy_document.web_lane.json
}

resource "aws_iam_user_policy_attachment" "michael_lane" {
  count = var.manage_team_users ? 1 : 0

  user       = aws_iam_user.team["michael"].name
  policy_arn = aws_iam_policy.web_lane.arn
}

# --- Shared deny boundary ---------------------------------------------------
#
# Explicit Deny beats any Allow, including a future broader attachment or a
# mistake by whoever edits this file next. Three things are off the table for
# both humans regardless of lane.

data "aws_iam_policy_document" "team_boundary" {
  # Terraform state is the whole account in one object: every ARN, every
  # resource attribute, and any value a provider marked sensitive.
  # ReadOnlyAccess would otherwise grant s3:GetObject on it.
  statement {
    sid       = "DenyTerraformState"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [local.tfstate_bucket_arn, "${local.tfstate_bucket_arn}/*"]
  }

  # Tenant HMAC keys. ReadOnlyAccess already excludes GetSecretValue; this
  # keeps that true if anything broader is ever attached.
  statement {
    sid    = "DenyTenantSecrets"
    effect = "Deny"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:PutSecretValue",
      "secretsmanager:UpdateSecret",
      "secretsmanager:DeleteSecret",
    ]
    resources = ["*"]
  }

  # No self-escalation: no editing users, policies, roles or keys -- their
  # own included. ReadOnlyAccess keeps iam:Get*/List* for inspection.
  statement {
    sid    = "DenyIamMutation"
    effect = "Deny"
    actions = [
      "iam:*AccessKey*",
      "iam:*Policy*",
      "iam:*Role*",
      "iam:*User*",
      "iam:*Group*",
      "iam:*LoginProfile*",
      "iam:*MFADevice*",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "team_boundary" {
  name        = "${local.name}-team-boundary"
  description = "Explicit denies applied to every human operator user."
  policy      = data.aws_iam_policy_document.team_boundary.json
}

resource "aws_iam_user_policy_attachment" "team_boundary" {
  for_each = local.team_users

  user       = aws_iam_user.team[each.key].name
  policy_arn = aws_iam_policy.team_boundary.arn
}
