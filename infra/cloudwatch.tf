resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/aws/lambda/${local.name}-vault-ingest"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "read" {
  name              = "/aws/lambda/${local.name}-vault-read"
  retention_in_days = 7
}

resource "aws_sns_topic" "alarms" {
  count = var.alarm_email == "" ? 0 : 1
  name  = "${local.name}-alarms"
}

resource "aws_sns_topic_subscription" "alarms_email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${local.name}-api-5xx"
  alarm_description   = "HTTP API 5xx count >= 5 in 5 minutes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.http.id
    Stage = aws_apigatewayv2_stage.default.name
  }

  alarm_actions = var.alarm_email == "" ? [] : [aws_sns_topic.alarms[0].arn]
}

# API Gateway access logs. Same 7-day retention as the Lambda groups so the
# whole request path expires together.
resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.name}-http"
  retention_in_days = 7
}
