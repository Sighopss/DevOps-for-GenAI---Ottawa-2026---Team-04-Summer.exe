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
  # Lambda bundle contents as {path-in-zip => path-on-disk}.
  #
  # This used to be source_dir = repo_root plus an exclude list built by walking
  # the whole repo. That walk covers infra/.terraform/ and vault/**/__pycache__,
  # both of which change *while Terraform runs*, so the file set differed between
  # plan and apply and the run died with "fileset returned an inconsistent
  # result". That is why no Lambda ever got created. Enumerating only vault/**.py
  # is deterministic: nothing under vault/ changes during an apply.
  #
  # It also stops shipping 24 test files and stale .pyc into production.
  lambda_py = setunion(
    fileset("${local.repo_root}/vault", "*.py"),
    fileset("${local.repo_root}/vault", "**/*.py"),
  )
  lambda_files = local.vault_present ? {
    for f in local.lambda_py : "vault/${f}" => "${local.repo_root}/vault/${f}"
    if !startswith(f, "tests/")
    } : {
    for f in fileset("${path.module}/stubs/placeholder", "**") :
    f => "${abspath(path.module)}/stubs/placeholder/${f}"
  }

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
