variable "project_name" {
  type        = string
  description = "Project name"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

variable "recovery_window_in_days" {
  type        = number
  description = "Number of days to retain secret after deletion"
  default     = 7
}

variable "kms_key_id" {
  type        = string
  description = "KMS key ID for encryption"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

# Secret values (sensitive)
variable "github_token" {
  type        = string
  description = "GitHub personal access token"
  default     = ""
  sensitive   = true
}

variable "github_webhook_secret" {
  type        = string
  description = "GitHub webhook secret"
  default     = ""
  sensitive   = true
}

variable "slack_token" {
  type        = string
  description = "Slack bot token"
  default     = ""
  sensitive   = true
}

variable "argocd_token" {
  type        = string
  description = "ArgoCD API token"
  default     = ""
  sensitive   = true
}

variable "argocd_server_url" {
  type        = string
  description = "ArgoCD server URL"
  default     = ""
}

variable "argocd_verify_ssl" {
  type        = bool
  description = "Verify SSL for ArgoCD"
  default     = true
}

variable "k8s_config" {
  type        = string
  description = "Kubernetes config (base64 encoded kubeconfig)"
  default     = ""
  sensitive   = true
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key"
  default     = ""
  sensitive   = true
}

variable "nvidia_nim_api_key" {
  type        = string
  description = "NVIDIA NIM API key"
  default     = ""
  sensitive   = true
}

# Configuration values
variable "github_repo" {
  type        = string
  description = "GitHub repository (org/repo)"
  default     = ""
}

variable "github_branch" {
  type        = string
  description = "Default GitHub branch"
  default     = "main"
}

variable "github_notification_channel" {
  type        = string
  description = "GitHub notification channel"
  default     = ""
}

variable "slack_channel_id" {
  type        = string
  description = "Slack channel ID for notifications"
  default     = ""
}

variable "slack_senior_dev_id" {
  type        = string
  description = "Slack user ID for senior developer"
  default     = ""
}

variable "slack_notification_channel" {
  type        = string
  description = "Slack notification channel name"
  default     = "#alerts"
}

variable "slack_search_channels" {
  type        = list(string)
  description = "Slack channels to search for historical incidents"
  default     = ["devops", "alerts", "incidents"]
}

variable "slack_time_window_days" {
  type        = number
  description = "Number of days to search Slack history"
  default     = 180
}

variable "slack_max_results" {
  type        = number
  description = "Maximum Slack search results"
  default     = 20
}

variable "llm_provider" {
  type        = string
  description = "LLM provider (openai, nvidia_nim, sagemaker)"
  default     = "openai"
}

variable "llm_model" {
  type        = string
  description = "LLM model name"
  default     = "gpt-3.5-turbo"
}

variable "llm_max_tokens" {
  type        = number
  description = "Maximum tokens for LLM"
  default     = 1024
}

variable "llm_temperature" {
  type        = number
  description = "LLM temperature"
  default     = 0.1
}

variable "llm_timeout_seconds" {
  type        = number
  description = "LLM timeout in seconds"
  default     = 30
}

variable "llm_fallback_enabled" {
  type        = bool
  description = "Enable LLM fallback"
  default     = true
}

variable "nvidia_nim_endpoint" {
  type        = string
  description = "NVIDIA NIM API endpoint"
  default     = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions"
}

variable "nvidia_nim_model" {
  type        = string
  description = "NVIDIA NIM model name"
  default     = "llama-3.1-nemotron-8b"
}

variable "confidence_threshold_prod" {
  type        = number
  description = "Confidence threshold for production"
  default     = 0.92
}

variable "confidence_threshold_staging" {
  type        = number
  description = "Confidence threshold for staging"
  default     = 0.85
}

variable "confidence_threshold_dev" {
  type        = number
  description = "Confidence threshold for development"
  default     = 0.75
}

variable "confidence_threshold_default" {
  type        = number
  description = "Default confidence threshold"
  default     = 0.85
}

variable "enable_auto_fix" {
  type        = bool
  description = "Enable automatic fixes"
  default     = true
}

variable "enable_slack_notifications" {
  type        = bool
  description = "Enable Slack notifications"
  default     = true
}

variable "enable_llm_analysis" {
  type        = bool
  description = "Enable LLM analysis"
  default     = true
}

variable "approval_prod_always" {
  type        = bool
  description = "Always require approval for production"
  default     = true
}

variable "approval_high_risk" {
  type        = bool
  description = "Always require approval for high-risk changes"
  default     = true
}

variable "approval_low_conf_threshold" {
  type        = number
  description = "Threshold for requiring approval on low confidence"
  default     = 0.9
}

# Secret rotation
variable "enable_secret_rotation" {
  type        = bool
  description = "Enable automatic secret rotation"
  default     = false
}

variable "rotation_lambda_arn" {
  type        = string
  description = "Lambda ARN for secret rotation"
  default     = ""
}

variable "rotation_days" {
  type        = number
  description = "Days between automatic rotation"
  default     = 30
}

variable "lambda_role_arns" {
  type        = list(string)
  description = "Lambda execution role ARNs that need access to secrets"
  default     = []
}
