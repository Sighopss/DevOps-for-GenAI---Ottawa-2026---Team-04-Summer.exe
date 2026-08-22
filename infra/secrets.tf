resource "aws_secretsmanager_secret" "tenant_a" {
  name        = "${local.name}/ingest/tenant-a"
  description = "Ingest X-Tenant-Key for tenant-a. Put the value with CLI; not in git."
  kms_key_id  = aws_kms_key.data.arn
}

resource "aws_secretsmanager_secret" "tenant_b" {
  name        = "${local.name}/ingest/tenant-b"
  description = "Ingest X-Tenant-Key for tenant-b. Put the value with CLI; not in git."
  kms_key_id  = aws_kms_key.data.arn
}
