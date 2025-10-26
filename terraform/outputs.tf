output "api_gateway_webhook_url" {
  value       = module.api_gateway.webhook_url
  description = "API Gateway webhook URL"
}

output "api_gateway_api_id" {
  value       = module.api_gateway.api_id
  description = "API Gateway API ID"
}

output "lambda_function_name" {
  value       = module.lambda.function_name
  description = "Lambda function name"
}

output "lambda_function_arn" {
  value       = module.lambda.function_arn
  description = "Lambda function ARN"
}

output "opensearch_endpoint" {
  value       = module.opensearch.endpoint
  description = "OpenSearch endpoint"
}

output "opensearch_dashboard_endpoint" {
  value       = module.opensearch.dashboard_endpoint
  description = "OpenSearch dashboard endpoint"
}

output "dynamodb_incidents_table_name" {
  value       = module.dynamodb.incidents_table_name
  description = "DynamoDB incidents table name"
}

output "dynamodb_resolutions_table_name" {
  value       = module.dynamodb.resolutions_table_name
  description = "DynamoDB resolutions table name"
}

output "dynamodb_metrics_table_name" {
  value       = module.dynamodb.metrics_table_name
  description = "DynamoDB metrics table name"
}

output "sagemaker_llm_endpoint_name" {
  value       = module.sagemaker.llm_endpoint_name
  description = "SageMaker LLM endpoint name"
}

output "sagemaker_embedding_endpoint_name" {
  value       = module.sagemaker.embedding_endpoint_name
  description = "SageMaker embedding endpoint name"
}

output "deployment_bucket_name" {
  value       = aws_s3_bucket.deployment.id
  description = "Deployment S3 bucket name"
}

output "model_artifacts_bucket_name" {
  value       = aws_s3_bucket.model_artifacts.id
  description = "Model artifacts S3 bucket name"
}

output "data_capture_bucket_name" {
  value       = aws_s3_bucket.data_capture.id
  description = "Data capture S3 bucket name"
}

output "slack_token_secret_arn" {
  value       = aws_secretsmanager_secret.slack_token.arn
  description = "Slack token secret ARN"
}

output "github_token_secret_arn" {
  value       = aws_secretsmanager_secret.github_token.arn
  description = "GitHub token secret ARN"
}

output "github_webhook_secret_arn" {
  value       = aws_secretsmanager_secret.github_webhook.arn
  description = "GitHub webhook secret ARN"
}

output "argocd_token_secret_arn" {
  value       = aws_secretsmanager_secret.argocd_token.arn
  description = "ArgoCD token secret ARN"
}

output "k8s_config_secret_arn" {
  value       = aws_secretsmanager_secret.k8s_config.arn
  description = "Kubernetes config secret ARN"
}

output "sns_topic_arn" {
  value       = var.create_sns_topic ? aws_sns_topic.alerts[0].arn : null
  description = "SNS topic ARN"
}

output "github_actions_role_arn" {
  value       = module.iam.github_actions_role_arn
  description = "GitHub Actions role ARN"
}

output "ci_deployer_access_key_id" {
  value       = module.iam.ci_deployer_access_key_id
  description = "CI deployer access key ID"
  sensitive   = true
}

output "ci_deployer_secret_access_key" {
  value       = module.iam.ci_deployer_secret_access_key
  description = "CI deployer secret access key"
  sensitive   = true
}