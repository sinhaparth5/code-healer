# GitHub Token Secret
resource "aws_secretsmanager_secret" "github_token" {
  name                    = "${var.project_name}/${var.environment}/github-token"
  description             = "GitHub API token for CodeHealer"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "github_token" {
  count         = var.github_token != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.github_token.id
  secret_string = var.github_token
}

# GitHub Webhook Secret
resource "aws_secretsmanager_secret" "github_webhook" {
  name                    = "${var.project_name}/${var.environment}/github-webhook-secret"
  description             = "GitHub webhook secret for signature verification"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "github_webhook" {
  count         = var.github_webhook_secret != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.github_webhook.id
  secret_string = var.github_webhook_secret
}

# Slack Token Secret
resource "aws_secretsmanager_secret" "slack_token" {
  name                    = "${var.project_name}/${var.environment}/slack-token"
  description             = "Slack API token for CodeHealer notifications"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "slack_token" {
  count         = var.slack_token != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.slack_token.id
  secret_string = var.slack_token
}

# ArgoCD Token Secret
resource "aws_secretsmanager_secret" "argocd_token" {
  name                    = "${var.project_name}/${var.environment}/argocd-token"
  description             = "ArgoCD API token for CodeHealer"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "argocd_token" {
  count         = var.argocd_token != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.argocd_token.id
  secret_string = jsonencode({
    token      = var.argocd_token
    server_url = var.argocd_server_url
    verify_ssl = var.argocd_verify_ssl
  })
}

# Kubernetes Config Secret
resource "aws_secretsmanager_secret" "k8s_config" {
  name                    = "${var.project_name}/${var.environment}/k8s-config"
  description             = "Kubernetes config for CodeHealer"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "k8s_config" {
  count         = var.k8s_config != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.k8s_config.id
  secret_string = var.k8s_config
}

# OpenAI API Key Secret (for LLM)
resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${var.project_name}/${var.environment}/openai-api-key"
  description             = "OpenAI API key for LLM integration"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  count         = var.openai_api_key != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = var.openai_api_key
}

# NVIDIA NIM API Key Secret (alternative LLM provider)
resource "aws_secretsmanager_secret" "nvidia_nim_api_key" {
  name                    = "${var.project_name}/${var.environment}/nvidia-nim-api-key"
  description             = "NVIDIA NIM API key for LLM integration"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "nvidia_nim_api_key" {
  count         = var.nvidia_nim_api_key != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.nvidia_nim_api_key.id
  secret_string = var.nvidia_nim_api_key
}

# Combined Application Config Secret (all non-sensitive config)
resource "aws_secretsmanager_secret" "app_config" {
  name                    = "${var.project_name}/${var.environment}/app-config"
  description             = "Application configuration for CodeHealer"
  recovery_window_in_days = var.recovery_window_in_days
  kms_key_id              = var.kms_key_id

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "app_config" {
  secret_id = aws_secretsmanager_secret.app_config.id
  secret_string = jsonencode({
    github = {
      repo                 = var.github_repo
      branch               = var.github_branch
      notification_channel = var.github_notification_channel
    }
    slack = {
      channel_id          = var.slack_channel_id
      senior_dev_id       = var.slack_senior_dev_id
      notification_channel = var.slack_notification_channel
      search_channels     = var.slack_search_channels
      time_window_days    = var.slack_time_window_days
      max_results         = var.slack_max_results
    }
    llm = {
      provider            = var.llm_provider
      model               = var.llm_model
      max_tokens          = var.llm_max_tokens
      temperature         = var.llm_temperature
      timeout_seconds     = var.llm_timeout_seconds
      fallback_enabled    = var.llm_fallback_enabled
    }
    nvidia_nim = {
      endpoint            = var.nvidia_nim_endpoint
      model               = var.nvidia_nim_model
    }
    confidence_thresholds = {
      production          = var.confidence_threshold_prod
      staging             = var.confidence_threshold_staging
      development         = var.confidence_threshold_dev
      default             = var.confidence_threshold_default
    }
    features = {
      enable_auto_fix               = var.enable_auto_fix
      enable_slack_notifications    = var.enable_slack_notifications
      enable_llm_analysis           = var.enable_llm_analysis
      approval_prod_always          = var.approval_prod_always
      approval_high_risk            = var.approval_high_risk
      approval_low_conf_threshold   = var.approval_low_conf_threshold
    }
  })
}

# Secret rotation for GitHub token (optional)
resource "aws_secretsmanager_secret_rotation" "github_token" {
  count               = var.enable_secret_rotation ? 1 : 0
  secret_id           = aws_secretsmanager_secret.github_token.id
  rotation_lambda_arn = var.rotation_lambda_arn

  rotation_rules {
    automatically_after_days = var.rotation_days
  }
}