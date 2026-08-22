data "archive_file" "lambda" {
  type        = "zip"
  output_path = "${path.module}/.build/lambda.zip"

  dynamic "source" {
    for_each = local.lambda_files
    content {
      content  = file(source.value)
      filename = source.key
    }
  }
}

resource "aws_lambda_function" "ingest" {
  function_name    = "${local.name}-vault-ingest"
  role             = aws_iam_role.ingest.arn
  handler          = "vault.handlers.ingest.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = var.lambda_timeout_seconds
  memory_size      = var.lambda_memory_mb
  architectures    = ["x86_64"]

  environment {
    variables = {
      TABLE               = aws_dynamodb_table.traces.name
      BUCKET              = aws_s3_bucket.payload.id
      KEY_ARN             = aws_kms_key.data.arn
      TENANT_A_SECRET_ARN = aws_secretsmanager_secret.tenant_a.arn
      TENANT_B_SECRET_ARN = aws_secretsmanager_secret.tenant_b.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.ingest]
}

resource "aws_lambda_function" "read" {
  function_name    = "${local.name}-vault-read"
  role             = aws_iam_role.read.arn
  handler          = "vault.handlers.read.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = var.lambda_timeout_seconds
  memory_size      = var.lambda_memory_mb
  architectures    = ["x86_64"]

  environment {
    variables = {
      TABLE               = aws_dynamodb_table.traces.name
      BUCKET              = aws_s3_bucket.payload.id
      KEY_ARN             = aws_kms_key.data.arn
      TENANT_A_SECRET_ARN = aws_secretsmanager_secret.tenant_a.arn
      TENANT_B_SECRET_ARN = aws_secretsmanager_secret.tenant_b.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.read]
}
