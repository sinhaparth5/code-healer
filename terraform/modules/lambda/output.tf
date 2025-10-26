output "function_name" {
  value = aws_lambda_function.codehealer.function_name
}

output "function_arn" {
  value = aws_lambda_function.codehealer.arn
}

output "function_invoke_arn" {
  value = aws_lambda_function.codehealer.invoke_arn
}

output "authorizer_function_name" {
  value = aws_lambda_function.authorizer.function_name
}

output "authorizer_function_arn" {
  value = aws_lambda_function.authorizer.arn
}

output "authorizer_invoke_arn" {
  value = aws_lambda_function.authorizer.invoke_arn
}

output "execution_role_arn" {
  value = aws_iam_role.lambda_execution.arn
}

output "execution_role_name" {
  value = aws_iam_role.lambda_execution.name
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.lambda.name
}

output "alias_arn" {
  value = aws_lambda_alias.live.arn
}