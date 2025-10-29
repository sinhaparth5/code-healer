variable "project_name" {
  type        = string
  description = "Project name"
  default = "DevFlowFix"
}

variable "environment" {
  type        = string
  description = "Environment name"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
  default = "us-east-1"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs"
}

variable "enable_vpc" {
  type        = bool
  description = "Enable VPC configuration"
  default     = true
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key ARN for encryption"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Additional tags"
  default     = {}
}

variable "lambda_runtime" {
  type        = string
  description = "Lambda runtime"
  default     = "python3.11"
}

variable "lambda_timeout" {
  type        = number
  description = "Lambda timeout in seconds"
  default     = 300
}

variable "lambda_memory_size" {
  type        = number
  description = "Lambda memory size in MB"
  default     = 1024
}

variable "lambda_reserved_concurrent_executions" {
  type        = number
  description = "Lambda reserved concurrent executions"
  default     = 100
}

variable "lambda_additional_env_vars" {
  type        = map(string)
  description = "Additional Lambda environment variables"
  default     = {}
}

variable "log_level" {
  type        = string
  description = "Log level"
  default     = "INFO"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days"
  default     = 30
}

variable "confidence_threshold" {
  type        = string
  description = "Confidence threshold for auto-fix"
  default     = "0.85"
}

variable "auto_fix_enabled" {
  type        = string
  description = "Enable auto-fix"
  default     = "true"
}

variable "max_retry_attempts" {
  type        = string
  description = "Maximum retry attempts"
  default     = "3"
}

variable "enable_xray" {
  type        = bool
  description = "Enable AWS X-Ray tracing"
  default     = true
}

variable "api_gateway_logging_level" {
  type        = string
  description = "API Gateway logging level"
  default     = "INFO"
}

variable "api_gateway_enable_data_trace" {
  type        = bool
  description = "Enable API Gateway data trace"
  default     = false
}

variable "api_gateway_throttle_burst_limit" {
  type        = number
  description = "API Gateway throttle burst limit"
  default     = 5000
}

variable "api_gateway_throttle_rate_limit" {
  type        = number
  description = "API Gateway throttle rate limit"
  default     = 10000
}

variable "sagemaker_llm_container_image" {
  type        = string
  description = "SageMaker LLM container image"
  default     = "mock-llm:latest" 
}

variable "sagemaker_llm_model_data_url" {
  type        = string
  description = "SageMaker LLM model data URL"
  default     = null
}

variable "sagemaker_llm_environment_vars" {
  type        = map(string)
  description = "SageMaker LLM environment variables"
  default     = {}
}

variable "sagemaker_llm_instance_count" {
  type        = number
  description = "SageMaker LLM instance count"
  default     = 1
}

variable "sagemaker_llm_instance_type" {
  type        = string
  description = "SageMaker LLM instance type"
  default     = "ml.g5.xlarge"
}

variable "sagemaker_llm_serverless_max_concurrency" {
  type        = number
  description = "SageMaker LLM serverless max concurrency"
  default     = 20
}

variable "sagemaker_llm_serverless_memory_size" {
  type        = number
  description = "SageMaker LLM serverless memory size"
  default     = 6144
}

variable "sagemaker_embedding_container_image" {
  type        = string
  description = "SageMaker embedding container image"
  default     = "mock-embedding:latest"
}

variable "sagemaker_embedding_model_data_url" {
  type        = string
  description = "SageMaker embedding model data URL"
  default     = null
}

variable "sagemaker_embedding_environment_vars" {
  type        = map(string)
  description = "SageMaker embedding environment variables"
  default     = {}
}

variable "sagemaker_embedding_instance_count" {
  type        = number
  description = "SageMaker embedding instance count"
  default     = 1
}

variable "sagemaker_embedding_instance_type" {
  type        = string
  description = "SageMaker embedding instance type"
  default     = "ml.g5.xlarge"
}

variable "sagemaker_embedding_serverless_max_concurrency" {
  type        = number
  description = "SageMaker embedding serverless max concurrency"
  default     = 50
}

variable "sagemaker_embedding_serverless_memory_size" {
  type        = number
  description = "SageMaker embedding serverless memory size"
  default     = 4096
}

variable "sagemaker_enable_data_capture" {
  type        = bool
  description = "Enable SageMaker data capture"
  default     = true
}

variable "sagemaker_data_capture_sampling_percentage" {
  type        = number
  description = "SageMaker data capture sampling percentage"
  default     = 10
}

variable "sagemaker_max_concurrent_invocations" {
  type        = number
  description = "SageMaker max concurrent invocations"
  default     = 20
}

variable "sagemaker_llm_latency_threshold_ms" {
  type        = number
  description = "SageMaker LLM latency threshold in ms"
  default     = 30000
}

variable "sagemaker_embedding_latency_threshold_ms" {
  type        = number
  description = "SageMaker embedding latency threshold in ms"
  default     = 5000
}

variable "sagemaker_enable_autoscaling" {
  type        = bool
  description = "Enable SageMaker autoscaling"
  default     = true
}

variable "sagemaker_llm_min_capacity" {
  type        = number
  description = "SageMaker LLM min capacity"
  default     = 1
}

variable "sagemaker_llm_max_capacity" {
  type        = number
  description = "SageMaker LLM max capacity"
  default     = 5
}

variable "sagemaker_llm_target_invocations_per_instance" {
  type        = number
  description = "SageMaker LLM target invocations per instance"
  default     = 100
}

variable "sagemaker_embedding_min_capacity" {
  type        = number
  description = "SageMaker embedding min capacity"
  default     = 1
}

variable "sagemaker_embedding_max_capacity" {
  type        = number
  description = "SageMaker embedding max capacity"
  default     = 5
}

variable "sagemaker_embedding_target_invocations_per_instance" {
  type        = number
  description = "SageMaker embedding target invocations per instance"
  default     = 200
}

variable "opensearch_engine_version" {
  type        = string
  description = "OpenSearch engine version"
  default     = "OpenSearch_2.11"
}

variable "opensearch_instance_type" {
  type        = string
  description = "OpenSearch instance type"
  default     = "r6g.large.search"
}

variable "opensearch_instance_count" {
  type        = number
  description = "OpenSearch instance count"
  default     = 2
}

variable "opensearch_dedicated_master_enabled" {
  type        = bool
  description = "Enable OpenSearch dedicated master"
  default     = true
}

variable "opensearch_dedicated_master_type" {
  type        = string
  description = "OpenSearch dedicated master type"
  default     = "r6g.large.search"
}

variable "opensearch_dedicated_master_count" {
  type        = number
  description = "OpenSearch dedicated master count"
  default     = 3
}

variable "opensearch_zone_awareness_enabled" {
  type        = bool
  description = "Enable OpenSearch zone awareness"
  default     = true
}

variable "opensearch_availability_zone_count" {
  type        = number
  description = "OpenSearch availability zone count"
  default     = 2
}

variable "opensearch_warm_enabled" {
  type        = bool
  description = "Enable OpenSearch warm storage"
  default     = false
}

variable "opensearch_warm_count" {
  type        = number
  description = "OpenSearch warm node count"
  default     = 0
}

variable "opensearch_warm_type" {
  type        = string
  description = "OpenSearch warm node type"
  default     = "ultrawarm1.medium.search"
}

variable "opensearch_volume_type" {
  type        = string
  description = "OpenSearch volume type"
  default     = "gp3"
}

variable "opensearch_volume_size" {
  type        = number
  description = "OpenSearch volume size in GB"
  default     = 100
}

variable "opensearch_iops" {
  type        = number
  description = "OpenSearch IOPS"
  default     = 3000
}

variable "opensearch_throughput" {
  type        = number
  description = "OpenSearch throughput"
  default     = 125
}

variable "opensearch_custom_endpoint_enabled" {
  type        = bool
  description = "Enable OpenSearch custom endpoint"
  default     = false
}

variable "opensearch_custom_endpoint" {
  type        = string
  description = "OpenSearch custom endpoint"
  default     = null
}

variable "opensearch_custom_endpoint_certificate_arn" {
  type        = string
  description = "OpenSearch custom endpoint certificate ARN"
  default     = null
}

variable "opensearch_internal_user_database_enabled" {
  type        = bool
  description = "Enable OpenSearch internal user database"
  default     = false
}

variable "opensearch_master_user_arn" {
  type        = string
  description = "OpenSearch master user ARN"
  default     = null
}

variable "opensearch_master_user_name" {
  type        = string
  description = "OpenSearch master user name"
  default     = null
}

variable "opensearch_master_user_password" {
  type        = string
  description = "OpenSearch master user password"
  default     = null
  sensitive   = true
}

variable "opensearch_allowed_cidr_blocks" {
  type        = list(string)
  description = "OpenSearch allowed CIDR blocks"
}

variable "opensearch_enable_slow_logs" {
  type        = bool
  description = "Enable OpenSearch slow logs"
  default     = true
}

variable "opensearch_enable_application_logs" {
  type        = bool
  description = "Enable OpenSearch application logs"
  default     = true
}

variable "opensearch_enable_audit_logs" {
  type        = bool
  description = "Enable OpenSearch audit logs"
  default     = true
}

variable "opensearch_knn_index_thread_qty" {
  type        = string
  description = "OpenSearch k-NN index thread quantity"
  default     = "1"
}

variable "opensearch_knn_memory_circuit_breaker_limit" {
  type        = string
  description = "OpenSearch k-NN memory circuit breaker limit"
  default     = "50"
}

variable "opensearch_auto_tune_enabled" {
  type        = bool
  description = "Enable OpenSearch auto-tune"
  default     = true
}

variable "opensearch_auto_tune_maintenance_start" {
  type        = string
  description = "OpenSearch auto-tune maintenance start time"
  default     = "2024-01-01T00:00:00Z"
}

variable "opensearch_auto_tune_maintenance_duration" {
  type        = number
  description = "OpenSearch auto-tune maintenance duration in hours"
  default     = 2
}

variable "opensearch_auto_tune_maintenance_cron" {
  type        = string
  description = "OpenSearch auto-tune maintenance cron"
  default     = "cron(0 3 ? * SUN *)"
}

variable "opensearch_snapshot_start_hour" {
  type        = number
  description = "OpenSearch snapshot start hour"
  default     = 3
}

variable "opensearch_free_storage_threshold_mb" {
  type        = number
  description = "OpenSearch free storage threshold in MB"
  default     = 10240
}

variable "opensearch_cpu_threshold_percent" {
  type        = number
  description = "OpenSearch CPU threshold percentage"
  default     = 80
}

variable "opensearch_jvm_memory_threshold_percent" {
  type        = number
  description = "OpenSearch JVM memory threshold percentage"
  default     = 85
}

variable "opensearch_master_cpu_threshold_percent" {
  type        = number
  description = "OpenSearch master CPU threshold percentage"
  default     = 50
}

variable "dynamodb_billing_mode" {
  type        = string
  description = "DynamoDB billing mode"
  default     = "PAY_PER_REQUEST"
}

variable "dynamodb_read_capacity" {
  type        = number
  description = "DynamoDB read capacity"
  default     = 5
}

variable "dynamodb_write_capacity" {
  type        = number
  description = "DynamoDB write capacity"
  default     = 5
}

variable "dynamodb_gsi_read_capacity" {
  type        = number
  description = "DynamoDB GSI read capacity"
  default     = 5
}

variable "dynamodb_gsi_write_capacity" {
  type        = number
  description = "DynamoDB GSI write capacity"
  default     = 5
}

variable "dynamodb_enable_ttl" {
  type        = bool
  description = "Enable DynamoDB TTL"
  default     = true
}

variable "dynamodb_enable_point_in_time_recovery" {
  type        = bool
  description = "Enable DynamoDB point-in-time recovery"
  default     = true
}

variable "dynamodb_enable_streams" {
  type        = bool
  description = "Enable DynamoDB streams"
  default     = false
}

variable "dynamodb_stream_view_type" {
  type        = string
  description = "DynamoDB stream view type"
  default     = "NEW_AND_OLD_IMAGES"
}

variable "dynamodb_enable_autoscaling" {
  type        = bool
  description = "Enable DynamoDB autoscaling"
  default     = true
}

variable "dynamodb_autoscaling_read_max_capacity" {
  type        = number
  description = "DynamoDB autoscaling read max capacity"
  default     = 100
}

variable "dynamodb_autoscaling_write_max_capacity" {
  type        = number
  description = "DynamoDB autoscaling write max capacity"
  default     = 100
}

variable "dynamodb_autoscaling_read_target_utilization" {
  type        = number
  description = "DynamoDB autoscaling read target utilization"
  default     = 70
}

variable "dynamodb_autoscaling_write_target_utilization" {
  type        = number
  description = "DynamoDB autoscaling write target utilization"
  default     = 70
}

variable "dynamodb_scale_in_cooldown" {
  type        = number
  description = "DynamoDB scale-in cooldown in seconds"
  default     = 300
}

variable "dynamodb_scale_out_cooldown" {
  type        = number
  description = "DynamoDB scale-out cooldown in seconds"
  default     = 60
}

variable "alarm_actions" {
  type        = list(string)
  description = "CloudWatch alarm actions"
  default     = []
}

variable "sns_topic_arns" {
  type        = list(string)
  description = "SNS topic ARNs for notifications"
  default     = []
}

variable "create_sns_topic" {
  type        = bool
  description = "Create SNS topic for alerts"
  default     = true
}

variable "alert_email" {
  type        = string
  description = "Email for alerts"
  default     = ""
}

variable "data_capture_retention_days" {
  type        = number
  description = "Data capture retention in days"
  default     = 90
}

variable "secret_recovery_window_days" {
  type        = number
  description = "Secret recovery window in days"
  default     = 7
}

variable "enable_github_oidc" {
  type        = bool
  description = "Enable GitHub OIDC"
  default     = false
}

variable "github_oidc_provider_arn" {
  type        = string
  description = "GitHub OIDC provider ARN"
  default     = ""
}

variable "github_repo" {
  type        = string
  description = "GitHub repository"
  default     = ""
}

variable "create_ci_user" {
  type        = bool
  description = "Create CI user"
  default     = false
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

# Secret values
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

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key"
  default     = ""
  sensitive   = true
}

variable "argocd_token" {
  type        = string
  description = "ArgoCD API token"
  default     = ""
  sensitive   = true
}

variable "k8s_config" {
  type        = string
  description = "Kubernetes config"
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
variable "llm_provider" {
  type        = string
  description = "LLM provider"
  default     = "openai"
}

variable "slack_channel_id" {
  type        = string
  description = "Slack channel ID"
  default     = ""
}

variable "slack_senior_dev_id" {
  type        = string
  description = "Slack senior dev user ID"
  default     = ""
}