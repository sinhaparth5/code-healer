output "llm_endpoint_name" {
  value       = var.environment == "local" ? "http://host.docker.internal:8080" : aws_sagemaker_endpoint.llm[0].name
  description = "LLM endpoint name or mock URL"
}

output "llm_endpoint_arn" {
  value       = var.environment == "local" ? "arn:aws:sagemaker:us-east-1:000000000000:endpoint/mock-llm" : aws_sagemaker_endpoint.llm[0].arn
  description = "LLM endpoint ARN or mock ARN"
}

output "embedding_endpoint_name" {
  value       = var.environment == "local" ? "http://host.docker.internal:8081" : aws_sagemaker_endpoint.embedding[0].name
  description = "Embedding endpoint name or mock URL"
}

output "embedding_endpoint_arn" {
  value       = var.environment == "local" ? "arn:aws:sagemaker:us-east-1:000000000000:endpoint/mock-embedding" : aws_sagemaker_endpoint.embedding[0].arn
  description = "Embedding endpoint ARN or mock ARN"
}

output "llm_model_name" {
  value       = var.environment == "local" ? "mock-llm-model" : aws_sagemaker_model.llm[0].name
  description = "LLM model name"
}

output "embedding_model_name" {
  value       = var.environment == "local" ? "mock-embedding-model" : aws_sagemaker_model.embedding[0].name
  description = "Embedding model name"
}

output "execution_role_arn" {
  value       = var.environment == "local" ? "arn:aws:iam::000000000000:role/mock-sagemaker-role" : aws_iam_role.sagemaker_execution[0].arn
  description = "SageMaker execution role ARN"
}

output "execution_role_name" {
  value       = var.environment == "local" ? "mock-sagemaker-role" : aws_iam_role.sagemaker_execution[0].name
  description = "SageMaker execution role name"
}

output "llm_log_group_name" {
  value       = var.environment == "local" ? "/aws/sagemaker/mock-llm" : aws_cloudwatch_log_group.llm_endpoint[0].name
  description = "LLM CloudWatch log group name"
}

output "embedding_log_group_name" {
  value       = var.environment == "local" ? "/aws/sagemaker/mock-embedding" : aws_cloudwatch_log_group.embedding_endpoint[0].name
  description = "Embedding CloudWatch log group name"
}
