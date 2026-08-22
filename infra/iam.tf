data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ingest" {
  name               = "${local.name}-vault-ingest"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role" "read" {
  name               = "${local.name}-vault-read"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "ingest" {
  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.ingest.arn}:*"]
  }

  statement {
    sid    = "PutObjectTenantPrefix"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload",
    ]
    resources = [
      for tenant in local.tenants : "${aws_s3_bucket.payload.arn}/${tenant}/*"
    ]
  }

  statement {
    sid    = "DynamoWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
    ]
    resources = [aws_dynamodb_table.traces.arn]
  }

  statement {
    sid    = "KmsData"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey",
    ]
    resources = [aws_kms_key.data.arn]
  }

  statement {
    sid    = "ReadIngestSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = [
      aws_secretsmanager_secret.tenant_a.arn,
      aws_secretsmanager_secret.tenant_b.arn,
    ]
  }
}

data "aws_iam_policy_document" "read" {
  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.read.arn}:*"]
  }

  statement {
    sid    = "GetObjectTenantPrefix"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      for tenant in local.tenants : "${aws_s3_bucket.payload.arn}/${tenant}/*"
    ]
  }

  statement {
    sid    = "DynamoReadAndAuditWrite"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:PutItem",
    ]
    resources = [aws_dynamodb_table.traces.arn]
  }

  statement {
    sid    = "KmsData"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
    ]
    resources = [aws_kms_key.data.arn]
  }
}

resource "aws_iam_role_policy" "ingest" {
  name   = "vault-ingest"
  role   = aws_iam_role.ingest.id
  policy = data.aws_iam_policy_document.ingest.json
}

resource "aws_iam_role_policy" "read" {
  name   = "vault-read"
  role   = aws_iam_role.read.id
  policy = data.aws_iam_policy_document.read.json
}
