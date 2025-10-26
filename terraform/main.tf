terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

locals {
  common_tags = merge(
    var.tags,
    {
      Project     = var.project_name
      Environment = var.environment
    }
  )
}

module "iam" {
  source = "./modules/iam"

  project_name                   = var.project_name
  aws_region                     = var.aws_region
  aws_account_id                 = data.aws_caller_identity.current.account_id
  authorizer_lambda_arn          = module.lambda.authorizer_function_arn
  lambda_function_arn            = module.lambda.function_arn
  opensearch_domain_arn          = module.opensearch.domain_arn
  incidents_table_arn            = module.dynamodb.incidents_table_arn
  resolutions_table_arn          = module.dynamodb.resolutions_table_arn
  metrics_table_arn              = module.dynamodb.metrics_table_arn
  sagemaker_llm_endpoint_arn     = module.sagemaker.llm_endpoint_arn
  sagemaker_embedding_endpoint_arn = module.sagemaker.embedding_endpoint_arn
  secrets_kms_key_arn            = var.kms_key_arn
  sns_topic_arns                 = var.sns_topic_arns
  enable_github_oidc             = var.enable_github_oidc
  github_oidc_provider_arn       = var.github_oidc_provider_arn
  github_repo                    = var.github_repo
  deployment_bucket_arn          = aws_s3_bucket.deployment.arn
  create_ci_user                 = var.create_ci_user
  enable_xray                    = var.enable_xray
  enable_vpc                     = var.enable_vpc
  tags                           = local.common_tags
}

module "lambda" {
  source = "./modules/lambda"

  project_name                     = var.project_name
  environment                      = var.environment
  aws_region                       = var.aws_region
  aws_account_id                   = data.aws_caller_identity.current.account_id
  runtime                          = var.lambda_runtime
  timeout                          = var.lambda_timeout
  memory_size                      = var.lambda_memory_size
  log_level                        = var.log_level
  log_retention_days               = var.log_retention_days
  reserved_concurrent_executions   = var.lambda_reserved_concurrent_executions
  opensearch_endpoint              = module.opensearch.endpoint
  opensearch_domain_arn            = module.opensearch.domain_arn
  dynamodb_table_name              = module.dynamodb.incidents_table_name
  dynamodb_table_arn               = module.dynamodb.incidents_table_arn
  sagemaker_llm_endpoint           = module.sagemaker.llm_endpoint_name
  sagemaker_llm_endpoint_arn       = module.sagemaker.llm_endpoint_arn
  sagemaker_embedding_endpoint     = module.sagemaker.embedding_endpoint_name
  sagemaker_embedding_endpoint_arn = module.sagemaker.embedding_endpoint_arn
  slack_token_secret_name          = aws_secretsmanager_secret.slack_token.name
  github_token_secret_name         = aws_secretsmanager_secret.github_token.name
  github_webhook_secret_name       = aws_secretsmanager_secret.github_webhook.name
  argocd_token_secret_name         = aws_secretsmanager_secret.argocd_token.name
  k8s_config_secret_name           = aws_secretsmanager_secret.k8s_config.name
  confidence_threshold             = var.confidence_threshold
  auto_fix_enabled                 = var.auto_fix_enabled
  max_retry_attempts               = var.max_retry_attempts
  subnet_ids                       = var.enable_vpc ? var.subnet_ids : []
  security_group_ids               = var.enable_vpc ? [aws_security_group.lambda[0].id] : []
  enable_xray                      = var.enable_xray
  alarm_actions                    = var.alarm_actions
  additional_env_vars              = var.lambda_additional_env_vars
  tags                             = local.common_tags

  depends_on = [module.iam]
}

module "api_gateway" {
  source = "./modules/api_gateway"

  project_name                  = var.project_name
  stage_name                    = var.environment
  lambda_function_name          = module.lambda.function_name
  lambda_invoke_arn             = module.lambda.function_invoke_arn
  authorizer_lambda_invoke_arn  = module.lambda.authorizer_invoke_arn
  authorizer_role_arn           = module.iam.lambda_authorizer_role_arn
  cloudwatch_role_arn           = module.iam.api_gateway_cloudwatch_role_arn
  log_retention_days            = var.log_retention_days
  enable_xray                   = var.enable_xray
  logging_level                 = var.api_gateway_logging_level
  enable_data_trace             = var.api_gateway_enable_data_trace
  throttle_burst_limit          = var.api_gateway_throttle_burst_limit
  throttle_rate_limit           = var.api_gateway_throttle_rate_limit
}

module "sagemaker" {
  source = "./modules/sagemaker"

  project_name                          = var.project_name
  llm_container_image                   = var.sagemaker_llm_container_image
  llm_model_data_url                    = var.sagemaker_llm_model_data_url
  llm_environment_vars                  = var.sagemaker_llm_environment_vars
  llm_instance_count                    = var.sagemaker_llm_instance_count
  llm_instance_type                     = var.sagemaker_llm_instance_type
  llm_serverless_max_concurrency        = var.sagemaker_llm_serverless_max_concurrency
  llm_serverless_memory_size            = var.sagemaker_llm_serverless_memory_size
  embedding_container_image             = var.sagemaker_embedding_container_image
  embedding_model_data_url              = var.sagemaker_embedding_model_data_url
  embedding_environment_vars            = var.sagemaker_embedding_environment_vars
  embedding_instance_count              = var.sagemaker_embedding_instance_count
  embedding_instance_type               = var.sagemaker_embedding_instance_type
  embedding_serverless_max_concurrency  = var.sagemaker_embedding_serverless_max_concurrency
  embedding_serverless_memory_size      = var.sagemaker_embedding_serverless_memory_size
  model_artifacts_bucket_arn            = aws_s3_bucket.model_artifacts.arn
  data_capture_bucket_arn               = aws_s3_bucket.data_capture.arn
  data_capture_s3_uri                   = "s3://${aws_s3_bucket.data_capture.id}/sagemaker"
  async_output_s3_uri                   = "s3://${aws_s3_bucket.data_capture.id}/async"
  enable_data_capture                   = var.sagemaker_enable_data_capture
  data_capture_sampling_percentage      = var.sagemaker_data_capture_sampling_percentage
  max_concurrent_invocations            = var.sagemaker_max_concurrent_invocations
  log_retention_days                    = var.log_retention_days
  llm_latency_threshold_ms              = var.sagemaker_llm_latency_threshold_ms
  embedding_latency_threshold_ms        = var.sagemaker_embedding_latency_threshold_ms
  alarm_actions                         = var.alarm_actions
  enable_autoscaling                    = var.sagemaker_enable_autoscaling
  llm_min_capacity                      = var.sagemaker_llm_min_capacity
  llm_max_capacity                      = var.sagemaker_llm_max_capacity
  llm_target_invocations_per_instance   = var.sagemaker_llm_target_invocations_per_instance
  embedding_min_capacity                = var.sagemaker_embedding_min_capacity
  embedding_max_capacity                = var.sagemaker_embedding_max_capacity
  embedding_target_invocations_per_instance = var.sagemaker_embedding_target_invocations_per_instance
  tags                                  = local.common_tags
}

module "opensearch" {
  source = "./modules/opensearch"

  project_name                   = var.project_name
  aws_account_id                 = data.aws_caller_identity.current.account_id
  engine_version                 = var.opensearch_engine_version
  instance_type                  = var.opensearch_instance_type
  instance_count                 = var.opensearch_instance_count
  dedicated_master_enabled       = var.opensearch_dedicated_master_enabled
  dedicated_master_type          = var.opensearch_dedicated_master_type
  dedicated_master_count         = var.opensearch_dedicated_master_count
  zone_awareness_enabled         = var.opensearch_zone_awareness_enabled
  availability_zone_count        = var.opensearch_availability_zone_count
  warm_enabled                   = var.opensearch_warm_enabled
  warm_count                     = var.opensearch_warm_count
  warm_type                      = var.opensearch_warm_type
  volume_type                    = var.opensearch_volume_type
  volume_size                    = var.opensearch_volume_size
  iops                           = var.opensearch_iops
  throughput                     = var.opensearch_throughput
  kms_key_id                     = var.kms_key_arn
  custom_endpoint_enabled        = var.opensearch_custom_endpoint_enabled
  custom_endpoint                = var.opensearch_custom_endpoint
  custom_endpoint_certificate_arn = var.opensearch_custom_endpoint_certificate_arn
  internal_user_database_enabled = var.opensearch_internal_user_database_enabled
  master_user_arn                = var.opensearch_master_user_arn
  master_user_name               = var.opensearch_master_user_name
  master_user_password           = var.opensearch_master_user_password
  vpc_id                         = var.vpc_id
  subnet_ids                     = var.subnet_ids
  allowed_cidr_blocks            = var.opensearch_allowed_cidr_blocks
  access_policy_principals       = [module.iam.opensearch_access_policy_arn]
  enable_slow_logs               = var.opensearch_enable_slow_logs
  enable_application_logs        = var.opensearch_enable_application_logs
  enable_audit_logs              = var.opensearch_enable_audit_logs
  log_retention_days             = var.log_retention_days
  knn_index_thread_qty           = var.opensearch_knn_index_thread_qty
  knn_memory_circuit_breaker_limit = var.opensearch_knn_memory_circuit_breaker_limit
  auto_tune_enabled              = var.opensearch_auto_tune_enabled
  auto_tune_maintenance_start    = var.opensearch_auto_tune_maintenance_start
  auto_tune_maintenance_duration = var.opensearch_auto_tune_maintenance_duration
  auto_tune_maintenance_cron     = var.opensearch_auto_tune_maintenance_cron
  snapshot_start_hour            = var.opensearch_snapshot_start_hour
  free_storage_threshold_mb      = var.opensearch_free_storage_threshold_mb
  cpu_threshold_percent          = var.opensearch_cpu_threshold_percent
  jvm_memory_threshold_percent   = var.opensearch_jvm_memory_threshold_percent
  master_cpu_threshold_percent   = var.opensearch_master_cpu_threshold_percent
  alarm_actions                  = var.alarm_actions
  tags                           = local.common_tags
}

module "dynamodb" {
  source = "./modules/dynamodb"

  project_name                        = var.project_name
  billing_mode                        = var.dynamodb_billing_mode
  read_capacity                       = var.dynamodb_read_capacity
  write_capacity                      = var.dynamodb_write_capacity
  gsi_read_capacity                   = var.dynamodb_gsi_read_capacity
  gsi_write_capacity                  = var.dynamodb_gsi_write_capacity
  enable_ttl                          = var.dynamodb_enable_ttl
  enable_point_in_time_recovery       = var.dynamodb_enable_point_in_time_recovery
  kms_key_arn                         = var.kms_key_arn
  enable_streams                      = var.dynamodb_enable_streams
  stream_view_type                    = var.dynamodb_stream_view_type
  enable_autoscaling                  = var.dynamodb_enable_autoscaling
  autoscaling_read_max_capacity       = var.dynamodb_autoscaling_read_max_capacity
  autoscaling_write_max_capacity      = var.dynamodb_autoscaling_write_max_capacity
  autoscaling_read_target_utilization = var.dynamodb_autoscaling_read_target_utilization
  autoscaling_write_target_utilization = var.dynamodb_autoscaling_write_target_utilization
  scale_in_cooldown                   = var.dynamodb_scale_in_cooldown
  scale_out_cooldown                  = var.dynamodb_scale_out_cooldown
  alarm_actions                       = var.alarm_actions
  tags                                = local.common_tags
}

resource "aws_s3_bucket" "deployment" {
  bucket = "${var.project_name}-deployment-${data.aws_caller_identity.current.account_id}"

  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "deployment" {
  bucket = aws_s3_bucket.deployment.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.project_name}-model-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "data_capture" {
  bucket = "${var.project_name}-data-capture-${data.aws_caller_identity.current.account_id}"

  tags = local.common_tags
}

resource "aws_s3_bucket_lifecycle_configuration" "data_capture" {
  bucket = aws_s3_bucket.data_capture.id

  rule {
    id     = "expire-old-data"
    status = "Enabled"

    expiration {
      days = var.data_capture_retention_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_capture" {
  bucket = aws_s3_bucket.data_capture.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_capture" {
  bucket = aws_s3_bucket.data_capture.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_secretsmanager_secret" "slack_token" {
  name                    = "${var.project_name}/slack-token"
  description             = "Slack API token for CodeHealer"
  recovery_window_in_days = var.secret_recovery_window_days
  kms_key_id              = var.kms_key_arn

  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "github_token" {
  name                    = "${var.project_name}/github-token"
  description             = "GitHub API token for CodeHealer"
  recovery_window_in_days = var.secret_recovery_window_days
  kms_key_id              = var.kms_key_arn

  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "github_webhook" {
  name                    = "${var.project_name}/github-webhook-secret"
  description             = "GitHub webhook secret for CodeHealer"
  recovery_window_in_days = var.secret_recovery_window_days
  kms_key_id              = var.kms_key_arn

  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "argocd_token" {
  name                    = "${var.project_name}/argocd-token"
  description             = "ArgoCD API token for CodeHealer"
  recovery_window_in_days = var.secret_recovery_window_days
  kms_key_id              = var.kms_key_arn

  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "k8s_config" {
  name                    = "${var.project_name}/k8s-config"
  description             = "Kubernetes config for CodeHealer"
  recovery_window_in_days = var.secret_recovery_window_days
  kms_key_id              = var.kms_key_arn

  tags = local.common_tags
}

resource "aws_security_group" "lambda" {
  count       = var.enable_vpc ? 1 : 0
  name        = "${var.project_name}-lambda-sg"
  description = "Security group for Lambda functions"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-lambda-sg"
    }
  )
}

resource "aws_sns_topic" "alerts" {
  count             = var.create_sns_topic ? 1 : 0
  name              = "${var.project_name}-alerts"
  kms_master_key_id = var.kms_key_arn

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.create_sns_topic && var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_caller_identity" "current" {}