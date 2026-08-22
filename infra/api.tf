# HTTP API (API Gateway v2). GET /health has no Lambda.
# v2 does not support MOCK integrations (WebSocket only), so /health is a
# MOCK-equivalent: HTTP_PROXY to the static {"ok":true} object on the web origin.

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name}-http"
  protocol_type = "HTTP"
  description   = "TraceVault HTTP API"

  cors_configuration {
    allow_origins     = [local.web_origin]
    allow_methods     = ["GET", "POST", "OPTIONS"]
    allow_headers     = ["Authorization", "Content-Type", "X-Tenant-Key"]
    allow_credentials = false
    max_age           = 3600
  }
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.http.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-jwt"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.web.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
  }
}

resource "aws_apigatewayv2_integration" "health" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "GET"
  integration_uri        = "${local.web_origin}/health.json"
  payload_format_version = "1.0"
  timeout_milliseconds   = 5000
}

resource "aws_apigatewayv2_route" "health_get" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /health"
  target             = "integrations/${aws_apigatewayv2_integration.health.id}"
  authorization_type = "NONE"
}

resource "aws_apigatewayv2_integration" "ingest" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ingest.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = min(var.lambda_timeout_seconds * 1000, 30000)
}

resource "aws_apigatewayv2_route" "ingest_post" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /v1/traces"
  target             = "integrations/${aws_apigatewayv2_integration.ingest.id}"
  authorization_type = "NONE"
}

resource "aws_apigatewayv2_integration" "read" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.read.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = min(var.lambda_timeout_seconds * 1000, 30000)
}

resource "aws_apigatewayv2_route" "traces_get" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /v1/traces"
  target             = "integrations/${aws_apigatewayv2_integration.read.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "trace_id_get" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /v1/traces/{trace_id}"
  target             = "integrations/${aws_apigatewayv2_integration.read.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "audit_get" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /v1/traces/{trace_id}/audit"
  target             = "integrations/${aws_apigatewayv2_integration.read.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit   = var.api_throttle_burst
    throttling_rate_limit    = var.api_throttle_rate
    detailed_metrics_enabled = true
  }

  # Access logging. Without this there was no record of what hit the API at
  # all: a refused cross-tenant read (403) and a throttled request (429) both
  # left zero trace, and requests rejected by the JWT authorizer never reach a
  # Lambda, so they were invisible everywhere (issue #126).
  #
  # Deliberately absent from this format: Authorization, X-Tenant-Key, and any
  # request body. The tenant claim is recorded because it is the tenant id, not
  # a credential -- it is what makes an audit line answer "who".
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      ip                      = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      routeKey                = "$context.routeKey"
      path                    = "$context.path"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      integrationStatus       = "$context.integrationStatus"
      tenant                  = "$context.authorizer.claims['custom:tenant_id']"
    })
  }
}

resource "aws_lambda_permission" "ingest_apigw" {
  statement_id  = "AllowHttpApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/POST/v1/traces"
}

resource "aws_lambda_permission" "read_apigw" {
  statement_id  = "AllowHttpApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.read.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/GET/v1/traces*"
}

# Fronts the CloudFront distribution, not the HTTP API (#100).
#
# WAFv2 attaches to API Gateway *REST* APIs only; this stack uses an HTTP API,
# so `aws_wafv2_web_acl_association` failed on every apply and the ACL filtered
# nothing. CloudFront is the surface WAFv2 can protect here, and it is what the
# judge-facing Explorer is served from. CloudFront-scoped ACLs must live in
# us-east-1, which is this stack's region.
#
# `scope` is immutable, so this replaces the old REGIONAL ACL rather than
# updating it. The resource address stays `.api` to avoid a state move; the
# ACL's own name is corrected to `-cdn`.
resource "aws_wafv2_web_acl" "api" {
  name        = "${local.name}-cdn"
  description = "AWS managed common rules in front of the TraceVault CloudFront distribution"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use {
            count {}
          }
        }

        rule_action_override {
          name = "NoUserAgent_HEADER"
          action_to_use {
            count {}
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name}-common"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name}-api"
    sampled_requests_enabled   = true
  }
}

# No `aws_wafv2_web_acl_association` here on purpose: CloudFront is not
# associated through that resource. The distribution takes `web_acl_id`
# directly — see `web_acl_id` in cloudfront.tf.
