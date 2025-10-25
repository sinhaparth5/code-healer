environment = "dev"

lambda_memory_size = 512
lambda_timeout     = 180

opensearch_instance_type           = "t3.small.search"
opensearch_instance_count          = 1
opensearch_dedicated_master_enabled = false
opensearch_zone_awareness_enabled  = false
opensearch_volume_size             = 20

sagemaker_llm_instance_type              = "ml.g5.xlarge"
sagemaker_llm_instance_count             = 1
sagemaker_embedding_instance_type        = "ml.g5.xlarge"
sagemaker_embedding_instance_count       = 1
sagemaker_enable_autoscaling             = false

dynamodb_billing_mode = "PAY_PER_REQUEST"

log_retention_days = 7

auto_fix_enabled = "false"

create_sns_topic = true