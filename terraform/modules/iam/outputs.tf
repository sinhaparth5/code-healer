output "api_gateway_cloudwatch_role_arn" {
  value = aws_iam_role.api_gateway_cloudwatch.arn
}

output "api_gateway_cloudwatch_role_name" {
  value = aws_iam_role.api_gateway_cloudwatch.name
}

output "lambda_authorizer_role_arn" {
  value = aws_iam_role.lambda_authorizer.arn
}

output "lambda_authorizer_role_name" {
  value = aws_iam_role.lambda_authorizer.name
}

output "github_actions_role_arn" {
  value = var.enable_github_oidc ? aws_iam_role.github_actions[0].arn : null
}

output "github_actions_role_name" {
  value = var.enable_github_oidc ? aws_iam_role.github_actions[0].name : null
}

output "opensearch_access_policy_arn" {
  value = aws_iam_policy.opensearch_access.arn
}

output "dynamodb_access_policy_arn" {
  value = aws_iam_policy.dynamodb_access.arn
}

output "sagemaker_invoke_policy_arn" {
  value = aws_iam_policy.sagemaker_invoke.arn
}

output "secrets_access_policy_arn" {
  value = aws_iam_policy.secrets_access.arn
}

output "kubernetes_access_policy_arn" {
  value = aws_iam_policy.kubernetes_access.arn
}

output "github_api_access_policy_arn" {
  value = aws_iam_policy.github_api_access.arn
}

output "slack_api_access_policy_arn" {
  value = aws_iam_policy.slack_api_access.arn
}

output "argocd_api_access_policy_arn" {
  value = aws_iam_policy.argocd_api_access.arn
}

output "monitoring_role_arn" {
  value = aws_iam_role.monitoring.arn
}

output "monitoring_role_name" {
  value = aws_iam_role.monitoring.name
}

output "ci_deployer_user_name" {
  value = var.create_ci_user ? aws_iam_user.ci_deployer[0].name : null
}

output "ci_deployer_access_key_id" {
  value     = var.create_ci_user ? aws_iam_access_key.ci_deployer[0].id : null
  sensitive = true
}

output "ci_deployer_secret_access_key" {
  value     = var.create_ci_user ? aws_iam_access_key.ci_deployer[0].secret : null
  sensitive = true
}

output "xray_access_policy_arn" {
  value = var.enable_xray ? aws_iam_policy.xray_access[0].arn : null
}

output "vpc_access_policy_arn" {
  value = var.enable_vpc ? aws_iam_policy.vpc_access[0].arn : null
}