environment = "staging"

lambda_memory_size = 1024
lambda_timeout     = 300

opensearch_instance_type            = "r6g.large.search"
opensearch_instance_count           = 2
opensearch_dedicated_master_enabled = true
opensearch_zone_awareness_enabled   = true
opensearch_volume_size              = 50

sagemaker_llm_instance_type              = "ml.g5.xlarge"
sagemaker_llm_instance_count             = 1
sagemaker_embedding_instance_type        = "ml.g5.xlarge"
sagemaker_embedding_instance_count       = 1
sagemaker_enable_autoscaling             = true
sagemaker_llm_max_capacity               = 3
sagemaker_embedding_max_capacity         = 3

dynamodb_billing_mode = "PAY_PER_REQUEST"

log_retention_days = 14

auto_fix_enabled     = "true"
confidence_threshold = "0.90"

create_sns_topic = true