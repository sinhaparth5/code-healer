resource "aws_api_gateway_rest_api" "codehealer_webhook" {
  name = "${var.project_name}-webhook-api"
  description = "API Gateway for receiving GitHub webhook events"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-webhook-api"
      Component = "api-gateway"
      ManagedBy = "terraform"
    }
  )
}

# Root resources (/)
resource "aws_api_gateway_resource" "webhook" {
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  parent_id = aws_api_gateway_rest_api.codehealer_webhook.root_resource_id
  path_part = "webhook"
}

# POST method for webhook
resource "aws_api_gateway_method" "webhook_post" {
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = "POST"
  authorization = "NONE"

  request_parameters = {
    "method.request.header.X-Hub-Signature-256" = true
    "method.request.header.X-GitHub-Event" = true
  }
}

# Method request validator
resource "aws_api_gateway_request_validator" "webhook_validator" {
  name = "${var.project_name}-webhook-validator"
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  validate_request_body = true
  validate_request_parameters = true
}

# Lambda integration
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_post.http_method
  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri = var.lambda_invoke_arn

  request_templates = {
    "application/json" = ""
  }

  timeout_milliseconds = 29000
}

resource "aws_api_gateway_method_response" "webhook_response_200" {
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "webhook_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_post.http_method
  status_code = aws_api_gateway_method_response.webhook_response_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [ aws_api_gateway_integration.lambda_integration ]
}

resource "aws_api_gateway_deployment" "webhook_deployment" {
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.webhook.id,
      aws_api_gateway_method.webhook_post.id,
      aws_api_gateway_integration.lambda_integration.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [ aws_api_gateway_integration.lambda_integration ]
}

# Stage
resource "aws_api_gateway_stage" "webhook_stage" {
  deployment_id = aws_api_gateway_deployment.webhook_deployment.id
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  stage_name = var.stage_name

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId = "$context.requestId"
      ip = "$context.identity.sourceIp"
      caller = "$context.identity.caller"
      user = "$context.identity.user"
      requestTime = "$context.requestTime"
      httpMethod = "$context.httpMethod"
      resorucePath = "$context.resourcePath"
      status = "$context.status"
      protocol = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  xray_tracing_enabled = var.enable_xray_tracing

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.stage_name}"
      Stage = var.stage_name
      Component = "api-gateway"
    }
  )
}

# CloudWatch log group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name = "/aws/apigateway/${var.project_name}-webhooks"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-api-logs"
      Component = "logging"
    }
  )
}

# Method Settings (for throttling and logging)
resource "aws_api_gateway_method_settings" "webhook_settings" {
  rest_api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  stage_name = aws_api_gateway_stage.webhook_stage.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled = true
    logging_level = var.api_logging_level
    data_trace_enabled = var.enable_data_trace
    throttling_burst_limit = var.throttling_burst_limit
    throttling_rate_limit = var.throttling_rate_limit
  }
}

# Lambda permission to allow API Gateway to invoke
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id = "AllowAPIGatewayInvoke"
  action = "lambda:InvokeFunction"
  function_name = var.lamdba_function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.codehealer_webhook.execution_arn}/*/*"
}

# WAF Web ACL
resource "aws_wafv2_web_acl" "api_gateway_waf" {
  count = var.enable_waf ? 1 : 0

  name  = "${var.project_name}-api-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # Rate limiting rule
  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project_name}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  # Geographic restriction (optional)
  dynamic "rule" {
    for_each = length(var.allowed_countries) > 0 ? [1] : []

    content {
      name     = "GeoRestrictionRule"
      priority = 2

      action {
        block {}
      }

      statement {
        not_statement {
          statement {
            geo_match_statement {
              country_codes = var.allowed_countries
            }
          }
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${var.project_name}-geo-restriction"
        sampled_requests_enabled   = true
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project_name}-waf"
    sampled_requests_enabled   = true
  }

  tags = merge(
    var.tags,
    {
      Name      = "${var.project_name}-api-waf"
      Component = "security"
    }
  )
}

# Associate WAF with API Gateway
resource "aws_wafv2_web_acl_association" "api_gateway_waf_association" {
  count = var.enable_waf ? 1 : 0

  resource_arn = aws_api_gateway_stage.webhook_stage.arn
  web_acl_arn = aws_wafv2_web_acl.api_gateway_waf[0].arn
}

# Custom domain
resource "aws_api_gateway_domain_name" "custom_domain" {
  count = var.custom_domain_name != "" ? 1 : 0

  domain_name = var.custom_domain_name
  regional_certificate_arn = var.certificate_arn
  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    var.tags,
    {
      Name = var.custom_domain_name
      Component = "api-gateway"
    }
  )
}

# Base path mapping for custom domain
resource "aws_api_gateway_base_path_mapping" "custom_domain_mapping" {
  count = var.custom_domain_name != "" ? 1 : 0
  
  api_id = aws_api_gateway_rest_api.codehealer_webhook.id
  stage_name = aws_api_gateway_stage.webhook_stage.stage_name
  domain_name = aws_api_gateway_domain_name.custom_domain[0].domain_name
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_errors" {
  alarm_name = "${var.project_name}-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = "2"
  metric_name = "5XXError"
  namespace = "AWS/ApiGateway"
  period = "300"
  statistic = "Sum"
  threshold = var.error_threshold
  alarm_description = "This metric monitors API Gateway 5XX errors"
  treat_missing_data = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.codehealer_webhook.name
    Stage = aws_api_gateway_stage.webhook_stage.stage_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-api-5xx-alarm"
      Component = "monitoring"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_errors" {
  alarm_name          = "${var.project_name}-api-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.error_threshold * 2
  alarm_description   = "This metric monitors API Gateway 4XX errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.codehealer_webhook.name
    Stage   = aws_api_gateway_stage.webhook_stage.stage_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  tags = merge(
    var.tags,
    {
      Name      = "${var.project_name}-api-4xx-alarm"
      Component = "monitoring"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${var.project_name}-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = var.latency_threshold
  alarm_description   = "This metric monitors API Gateway latency"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.codehealer_webhook.name
    Stage   = aws_api_gateway_stage.webhook_stage.stage_name
  }

  alarm_actions = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  tags = merge(
    var.tags,
    {
      Name      = "${var.project_name}-api-latency-alarm"
      Component = "monitoring"
    }
  )
}