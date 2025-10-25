output "llm_endpoint_name" {
  value = aws_sagemaker_endpoint.llm.name
}

output "llm_endpoint_arn" {
  value = aws_sagemaker_endpoint.llm.arn
}

output "embedding_endpoint_name" {
  value = aws_sagemaker_endpoint.embedding.name
}

output "embedding_endpoint_arn" {
  value = aws_sagemaker_endpoint.embedding.arn
}

output "llm_model_name" {
  value = aws_sagemaker_model.llm.name
}

output "embedding_model_name" {
  value = aws_sagemaker_model.embedding.name
}

output "execution_role_arn" {
  value = aws_iam_role.sagemaker_execution.arn
}

output "execution_role_name" {
  value = aws_iam_role.sagemaker_execution.name
}

output "llm_log_group_name" {
  value = aws_cloudwatch_log_group.llm_endpoint.name
}

output "embedding_log_group_name" {
  value = aws_cloudwatch_log_group.embedding_endpoint.name
}