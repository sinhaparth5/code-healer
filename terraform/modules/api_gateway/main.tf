resource "aws_api_gateway_rest_api" "codehealer" {
  name = "${var.project_name}-api"
  description = "Codehealer webhook endpoint"

  endpoint_configuration {
    types = [ "REGIONAL" ]
  }
}

resource "aws_api_gateway_resource" "webhook" {
  rest_api_id = aws_api_gateway_rest_api.codehealer.id
  parent_id = aws_api_gateway_rest_api.codehealer.root_resource_id
  path_part = "webhook"
}

resource "aws_api_gateway_method" "webhook_post" {
  rest_api_id = aws_api_gateway_rest_api.codehealer.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = "POST"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.webhook_auth.id
}

resource "aws_api_gateway_authorizer" "webhook_auth" {
  name = "${var.project_name}-authorizer"
  rest_api_id = aws_api_gateway_rest_api.codehealer.id
  type = "REQUEST"
  authorizer_uri = var.authorizer_lambda_invoke_arn
  authorizer_credentials = var.authorizer_role_arn
  identity_source = "method.request.header.X-Hub-Signature-256"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.codehealer.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_post.http_method
  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri = var.lambda_invoke_arn
}

resource "aws_api_gateway_deployment" "codehealer" {
  rest_api_id = aws_api_gateway_rest_api.codehealer.id

  depends_on = [ aws_api_gateway_integration.lambda ]
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "codehealer" {
  deployment_id = aws_api_gateway_deployment.codehealer.id
  rest_api_id = aws_api_gateway_rest_api.codehealer.id
  stage_name = var.stage_name

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
        requestId = "$context.requestId"
        ip = "$context.identity.sourceIp"
        requestTime = "$context.requestTime"
        httpMethod = "$context.httpMethod"
        resourcePath = "$context.resourcePath"
        status = "$context.status"
        protocol = "$context.protocol"
        responseLength = "$context.responseLength"
    })
  }
  xray_tracing_enabled = var.enable_xray
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name = "/aws/apigateway/${var.project_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.codehealer.id
  stage_name = aws_api_gateway_stage.codehealer.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled = true
    logging_level = var.logging_level
    data_trace_enabled = var.enable_data_trace
    throttling_burst_limit = var.throttle_burst_limit
    throttling_rate_limit = var.throttle_rate_limit
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id = "AllowAPIGatewayInvoke"
  action = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.codehealer.execution_arn}/*/*"
}

resource "aws_api_gateway_account" "codehealer" {
  cloudwatch_role_arn = var.cloudwatch_role_arn
}