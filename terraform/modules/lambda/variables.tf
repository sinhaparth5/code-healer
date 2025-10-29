 variable "project_name" {
   type = string
 }

 variable "environment" {
   type = string
 }

 variable "aws_region" {
   type = string
 }

 variable "aws_account_id" {
   type = string
 }

 variable "runtime" {
    type = string
    default = "python3.11"
 }

 variable "timeout" {
   type = number
   default = 300
 }

 variable "memory_size" {
   type = number
   default = 1024
 }

 variable "log_level" {
   type = string
   default = "INFO"
 }

variable "log_retention_days" {
    type = number
    default = 30
}

variable "reserved_concurrent_executions" {
  type = number
  default = 100
}

variable "opensearch_endpoint" {
  type = string
}

variable "opensearch_domain_arn" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "dynamodb_table_arn" {
  type = string
}

variable "sagemaker_llm_endpoint" {
  type = string
}

variable "sagemaker_llm_endpoint_arn" {
  type = string
}

variable "sagemaker_embedding_endpoint" {
  type = string
}

variable "sagemaker_embedding_endpoint_arn" {
  type = string
}

variable "github_token_secret_arn" {
  type        = string
  description = "ARN of GitHub token secret"
}

variable "github_token_secret_name" {
  type        = string
  description = "Name of GitHub token secret"
}

variable "github_webhook_secret_arn" {
  type        = string
  description = "ARN of GitHub webhook secret"
}

variable "github_webhook_secret_name" {
  type        = string
  description = "Name of GitHub webhook secret"
}

variable "slack_token_secret_arn" {
  type        = string
  description = "ARN of Slack token secret"
}

variable "slack_token_secret_name" {
  type        = string
  description = "Name of Slack token secret"
}

variable "argocd_token_secret_arn" {
  type        = string
  description = "ARN of ArgoCD token secret"
}

variable "argocd_token_secret_name" {
  type        = string
  description = "Name of ArgoCD token secret"
}

variable "k8s_config_secret_arn" {
  type        = string
  description = "ARN of Kubernetes config secret"
}

variable "k8s_config_secret_name" {
  type        = string
  description = "Name of Kubernetes config secret"
}

variable "openai_api_key_secret_arn" {
  type        = string
  description = "ARN of OpenAI API key secret"
}

variable "openai_api_key_secret_name" {
  type        = string
  description = "Name of OpenAI API key secret"
}

variable "nvidia_nim_api_key_secret_arn" {
  type        = string
  description = "ARN of NVIDIA NIM API key secret"
}

variable "nvidia_nim_api_key_secret_name" {
  type        = string
  description = "Name of NVIDIA NIM API key secret"
}

variable "app_config_secret_arn" {
  type        = string
  description = "ARN of application config secret"
}

variable "app_config_secret_name" {
  type        = string
  description = "Name of application config secret"
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for secret decryption"
  default     = null
}

# Add feature flag variables
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

variable "confidence_threshold" {
  type = string
  default = "0.85"
}

variable "auto_fix_enabled" {
  type = string
  default = "true"
}

variable "max_retry_attempts" {
  type = string
  default = "3"
}

variable "subnet_ids" {
  type = list(string)
  default = [  ]
}

variable "security_group_ids" {
  type = list(string)
  default = [  ]
}

variable "enable_xray" {
  type = bool
  default = true
}

variable "alarm_actions" {
  type = list(string)
  default = [  ]
}

variable "additional_env_vars" {
  type = map(string)
  default = { }
}

variable "tags" {
  type = map(string)
  default = { }
}
