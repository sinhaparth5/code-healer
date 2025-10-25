output "api_id" {
  value = aws_api_gateway_rest_api.codehealer.id
}

output "api_endpoint" {
  value = aws_api_gateway_stage.codehealer.invoke_url
}

output "webhook_url" {
  value = "${aws_api_gateway_stage.codehealer.invoke_url}/webhook"
}

output "execution_arn" {
  value = aws_api_gateway_rest_api.codehealer.execution_arn
}

output "stage_arn" {
  value = aws_api_gateway_stage.codehealer.arn
}