output "ingest_url" {
  description = "POST /v1/traces (X-Tenant-Key, not Cognito)."
  value       = local.ingest_url
}

output "api_url" {
  description = "HTTP API base URL (no trailing slash). GET /health lives here."
  value       = local.api_url
}

output "cloudfront_url" {
  description = "HTTPS UI origin. Cognito callback/logout and CORS allow origin."
  value       = local.web_origin
}

output "user_pool_id" {
  description = "Cognito user pool id (NEXT_PUBLIC_COGNITO_USER_POOL_ID)."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_client_id" {
  description = "Cognito app client id (NEXT_PUBLIC_COGNITO_CLIENT_ID)."
  value       = aws_cognito_user_pool_client.web.id
}

output "cognito_domain" {
  description = "Hosted UI domain host only (no scheme). Prefix with https://."
  value       = "${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "table_name" {
  description = "DynamoDB traces table (PK tenant_id, SK trace_id, TTL expires_at)."
  value       = aws_dynamodb_table.traces.name
}

output "payload_bucket" {
  description = "SSE-KMS payload bucket. Objects under {tenant_id}/{trace_id}/."
  value       = aws_s3_bucket.payload.id
}

output "web_bucket" {
  description = "Private web origin bucket. Deploy Next export here; CloudFront OAC reads it."
  value       = aws_s3_bucket.web.id
}

output "oidc_role_arn" {
  description = "GitHub Actions OIDC role limited to this stack and this repo."
  value       = aws_iam_role.gha_oidc.arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution id for deploy invalidation."
  value       = aws_cloudfront_distribution.web.id
}

output "next_public_api_url" {
  description = "Michael: NEXT_PUBLIC_API_URL"
  value       = local.api_url
}

output "next_public_cognito_region" {
  description = "Michael: NEXT_PUBLIC_COGNITO_REGION"
  value       = var.aws_region
}

output "next_public_cognito_user_pool_id" {
  description = "Michael: NEXT_PUBLIC_COGNITO_USER_POOL_ID"
  value       = aws_cognito_user_pool.this.id
}

output "next_public_cognito_client_id" {
  description = "Michael: NEXT_PUBLIC_COGNITO_CLIENT_ID"
  value       = aws_cognito_user_pool_client.web.id
}

output "next_public_cognito_domain" {
  description = "Michael: NEXT_PUBLIC_COGNITO_DOMAIN (full host)."
  value       = "${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com"
}
