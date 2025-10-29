output "github_token_secret_arn" {
  value       = aws_secretsmanager_secret.github_token.arn
  description = "ARN of GitHub token secret"
}

output "github_token_secret_name" {
  value       = aws_secretsmanager_secret.github_token.name
  description = "Name of GitHub token secret"
}

output "github_webhook_secret_arn" {
  value       = aws_secretsmanager_secret.github_webhook.arn
  description = "ARN of GitHub webhook secret"
}

output "github_webhook_secret_name" {
  value       = aws_secretsmanager_secret.github_webhook.name
  description = "Name of GitHub webhook secret"
}

output "slack_token_secret_arn" {
  value       = aws_secretsmanager_secret.slack_token.arn
  description = "ARN of Slack token secret"
}

output "slack_token_secret_name" {
  value       = aws_secretsmanager_secret.slack_token.name
  description = "Name of Slack token secret"
}

output "argocd_token_secret_arn" {
  value       = aws_secretsmanager_secret.argocd_token.arn
  description = "ARN of ArgoCD token secret"
}

output "argocd_token_secret_name" {
  value       = aws_secretsmanager_secret.argocd_token.name
  description = "Name of ArgoCD token secret"
}

output "k8s_config_secret_arn" {
  value       = aws_secretsmanager_secret.k8s_config.arn
  description = "ARN of Kubernetes config secret"
}

output "k8s_config_secret_name" {
  value       = aws_secretsmanager_secret.k8s_config.name
  description = "Name of Kubernetes config secret"
}

output "openai_api_key_secret_arn" {
  value       = aws_secretsmanager_secret.openai_api_key.arn
  description = "ARN of OpenAI API key secret"
}

output "openai_api_key_secret_name" {
  value       = aws_secretsmanager_secret.openai_api_key.name
  description = "Name of OpenAI API key secret"
}

output "nvidia_nim_api_key_secret_arn" {
  value       = aws_secretsmanager_secret.nvidia_nim_api_key.arn
  description = "ARN of NVIDIA NIM API key secret"
}

output "nvidia_nim_api_key_secret_name" {
  value       = aws_secretsmanager_secret.nvidia_nim_api_key.name
  description = "Name of NVIDIA NIM API key secret"
}

output "app_config_secret_arn" {
  value       = aws_secretsmanager_secret.app_config.arn
  description = "ARN of application config secret"
}

output "app_config_secret_name" {
  value       = aws_secretsmanager_secret.app_config.name
  description = "Name of application config secret"
}

output "all_secret_arns" {
  value = [
    aws_secretsmanager_secret.github_token.arn,
    aws_secretsmanager_secret.github_webhook.arn,
    aws_secretsmanager_secret.slack_token.arn,
    aws_secretsmanager_secret.argocd_token.arn,
    aws_secretsmanager_secret.k8s_config.arn,
    aws_secretsmanager_secret.openai_api_key.arn,
    aws_secretsmanager_secret.nvidia_nim_api_key.arn,
    aws_secretsmanager_secret.app_config.arn,
  ]
  description = "List of all secret ARNs"
}
