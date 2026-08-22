data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  name       = "${var.project}-${var.env}"
  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition
  tenants    = ["tenant-a", "tenant-b"]

  cognito_domain_prefix = var.cognito_domain_prefix != "" ? var.cognito_domain_prefix : "tv-${var.env}-${data.aws_caller_identity.current.account_id}"

  web_origin = "https://${aws_cloudfront_distribution.web.domain_name}"
  api_url    = aws_apigatewayv2_api.http.api_endpoint
  ingest_url = "${aws_apigatewayv2_api.http.api_endpoint}/v1/traces"

  repo_root     = abspath("${path.module}/..")
  vault_present = length(fileset(local.repo_root, "vault/**/*.py")) > 0
  lambda_src    = local.vault_present ? local.repo_root : "${path.module}/stubs/placeholder"
  lambda_excludes = local.vault_present ? [
    for f in fileset(local.repo_root, "**") : f if !startswith(f, "vault/")
  ] : []

  bedrock_model_arns = concat(
    [
      for id in var.bedrock_model_ids :
      "arn:${local.partition}:bedrock:${var.aws_region}::foundation-model/${id}"
    ],
    [
      for id in var.bedrock_model_ids :
      "arn:${local.partition}:bedrock:${var.aws_region}:${local.account_id}:inference-profile/${id}"
    ],
  )
}
