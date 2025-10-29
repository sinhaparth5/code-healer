environment = "local"

# # Network - LocalStack doesn't need real VPC
# vpc_id     = "vpc-local"
# subnet_ids = ["subnet-12345678", "subnet-87654321"]
enable_vpc = false
vpc_id     = ""
subnet_ids = []

# Lambda configuration (minimal for local)
lambda_memory_size = 512
lambda_timeout     = 60
lambda_reserved_concurrent_executions = 10

# Disable OpenSearch (using Elasticsearch instead)
# OpenSearch settings are ignored in local mode

# Disable SageMaker (using mock service)
# SageMaker settings point to mock service
sagemaker_llm_instance_type              = "ml.mock.small"
sagemaker_llm_instance_count             = 1
sagemaker_embedding_instance_type        = "ml.mock.small"
sagemaker_embedding_instance_count       = 1
sagemaker_enable_autoscaling             = false

# DynamoDB
dynamodb_billing_mode = "PAY_PER_REQUEST"

# Logging (short retention for local)
log_retention_days = 1

# Features
auto_fix_enabled = "false"  # Disable for local testing
enable_xray = false         # Not supported in LocalStack
create_sns_topic = true

# OpenSearch alternatives
opensearch_allowed_cidr_blocks = ["0.0.0.0/0"]
opensearch_instance_type           = "t3.small.search"
opensearch_instance_count          = 1
opensearch_dedicated_master_enabled = false
opensearch_zone_awareness_enabled  = false
opensearch_volume_size             = 10

# Secrets (mock values)
github_token          = "mock-github-token"
github_webhook_secret = "mock-webhook-secret"
slack_token           = "mock-slack-token"
openai_api_key        = "mock-openai-key"

# Configuration
github_repo         = "test-org/test-repo"
slack_channel_id    = "C0000000000"
slack_senior_dev_id = "U0000000000"
llm_provider        = "openai"
