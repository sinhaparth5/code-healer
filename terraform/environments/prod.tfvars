environment = "prod"

lambda_memory_size                 = 2048
lambda_timeout                     = 300
lambda_reserved_concurrent_executions = 200

opensearch_instance_type            = "r6g.xlarge.search"
opensearch_instance_count           = 3
opensearch_dedicated_master_enabled = true
opensearch_dedicated_master_count   = 3
opensearch_zone_awareness_enabled   = true
opensearch_availability_zone_count  = 3
opensearch_volume_size              = 200
opensearch_enable_audit_logs        = true

sagemaker_llm_instance_type              = "ml.g5.2xlarge"
sagemaker_llm_instance_count             = 2
sagemaker_embedding_instance_type        = "ml.g5.xlarge"
sagemaker_embedding_instance_count       = 2
sagemaker_enable_autoscaling             = true
sagemaker_llm_max_capacity               = 5
sagemaker_embedding_max_capacity         = 5

dynamodb_billing_mode                     = "PAY_PER_REQUEST"
dynamodb_enable_point_in_time_recovery    = true

log_retention_days = 30

auto_fix_enabled     = "true"
confidence_threshold = "0.85"

create_sns_topic = true

enable_xray = true