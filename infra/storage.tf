resource "aws_s3_bucket" "payload" {
  bucket = "${local.name}-payloads-${local.account_id}"
}

resource "aws_s3_bucket_ownership_controls" "payload" {
  bucket = aws_s3_bucket.payload.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "payload" {
  bucket                  = aws_s3_bucket.payload.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "payload" {
  bucket = aws_s3_bucket.payload.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_policy" "payload" {
  bucket = aws_s3_bucket.payload.id
  policy = data.aws_iam_policy_document.payload.json
}

data "aws_iam_policy_document" "payload" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.payload.arn,
      "${aws_s3_bucket.payload.arn}/*",
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket" "web" {
  bucket = "${local.name}-web-${local.account_id}"
}

resource "aws_s3_bucket_ownership_controls" "web" {
  bucket = aws_s3_bucket.web.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "web" {
  bucket = aws_s3_bucket.web.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id
  policy = data.aws_iam_policy_document.web.json
}

data "aws_iam_policy_document" "web" {
  statement {
    sid    = "AllowCloudFrontOac"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.web.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.web.arn]
    }
  }

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.web.arn,
      "${aws_s3_bucket.web.arn}/*",
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_object" "health" {
  bucket       = aws_s3_bucket.web.id
  key          = "health.json"
  content      = "{\"ok\":true}"
  content_type = "application/json"
}

resource "aws_dynamodb_table" "traces" {
  name         = "${local.name}-traces"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenant_id"
  range_key    = "trace_id"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "trace_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.data.arn
  }
}

# Payload objects must not outlive the DynamoDB row that points at them.
# The vault code writes expires_at from VAULT_TTL_DAYS; both read
# var.retention_days so the two cannot drift (issue #121).
resource "aws_s3_bucket_lifecycle_configuration" "payload" {
  bucket = aws_s3_bucket.payload.id

  rule {
    id     = "expire-with-dynamodb-ttl"
    status = "Enabled"

    filter {}

    expiration {
      days = var.retention_days
    }

    # A failed multipart upload otherwise bills forever and is invisible.
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}
