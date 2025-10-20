output "api_gateway_id" {
  description = "ID of the API Gateway REST API"
  value = aws_api_gateway_rest_api.codehealer_webhook.id
}

output "api_gateway_arn" {
  description = "ARN of the API Gateway REST API"
  value = aws_api_gateway_rest_api.codehealer_webhook.arn
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway REST API"
  value = aws_api_gateway_rest_api.codehealer_webhook.execution_arn
}

output "api_gateway_invoke_url" {
  description = "Invoke URL for the API Gateway stage"
  value = aws_api_gateway_stage.webhook_stage.invoke_url
}

output "webhook_url" {
  description = "Complete webhook URL to configure in GitHub"
  value = "${aws_api_gateway_stage.webhook_stage.invoke_url}/webhook"
}

output "api_gateway_stage_name" {
  description = "Name of the API Gateway stage"
  value = aws_api_gateway_stage.webhook_stage.stage_name
}

output "api_gateway_stage_arn" {
    description = "ARN of the API Gateway stage"
    value = aws_api_gateway_stage.webhook_stage.arn
}

output "cloudwatch_log_group_name" {
  description = "Name of the Cloudwatch log group for API Gateway"
  value = aws_cloudwatch_log_group.api_gateway_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the Cloudwatch log group for API Gateway"
  value = aws_cloudwatch_log_group.api_gateway_logs.arn
}

output "custom_domain_name" {
  description = "Custom domain name"
  value = var.custom_domain_name != "" ? aws_api_gateway_domain_name.custom_domain[0].domain_name : ""
}

output "custom_domain_regional_domain_name" {
  description = "Regional domain name for Route53 configuration"
  value       = var.custom_domain_name != "" ? aws_api_gateway_domain_name.custom_domain[0].regional_domain_name : ""
}

output "custom_domain_regional_zone_id" {
  description = "Regional zone ID for Route53 configuration"
  value       = var.custom_domain_name != "" ? aws_api_gateway_domain_name.custom_domain[0].regional_zone_id : ""
}

output "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL (if enabled)"
  value       = var.enable_waf ? aws_wafv2_web_acl.api_gateway_waf[0].arn : ""
}

output "alarm_5xx_name" {
  description = "Name of the 5XX error CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_5xx_errors.alarm_name
}

output "alarm_4xx_name" {
  description = "Name of the 4XX error CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_4xx_errors.alarm_name
}

output "alarm_latency_name" {
  description = "Name of the latency CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_latency.alarm_name
}