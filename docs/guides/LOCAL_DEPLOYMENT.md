# Local Development Guide

Quick setup and testing guide for CodeHealer on LocalStack.

## Prerequisites

- Docker and Docker Compose installed
- Terraform >= 1.5.0
- AWS CLI

## Quick Start

### 1. Start Environment

```bash
./scripts/start-local.sh
```

This starts:
- LocalStack (AWS services)
- Elasticsearch (replaces OpenSearch)
- Mock SageMaker (LLM + Embeddings)

### 2. Verify Services

```bash
./scripts/test-local.sh
```

Check individual services:
```bash
# LocalStack
curl http://localhost:4566/_localstack/health

# Elasticsearch
curl http://localhost:9200

# Mock LLM
curl http://localhost:8080/health

# Mock Embeddings
curl http://localhost:8081/health
```

### 3. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply -var-file="environments/local.tfvars"
```

### 4. Test Lambda Function

```bash
# Invoke Lambda
aws --endpoint-url=http://localhost:4566 lambda invoke \
    --function-name codehealer-handler \
    --payload '{"body": "{\"test\": \"data\"}"}' \
    output.json

# View response
cat output.json
```

### 5. View Logs

```bash
# All services
docker-compose -f docker-compose.localstack.yml logs -f

# Specific service
docker-compose -f docker-compose.localstack.yml logs -f mock-sagemaker
docker-compose -f docker-compose.localstack.yml logs -f localstack
docker-compose -f docker-compose.localstack.yml logs -f elasticsearch
```

### 6. Stop Environment

```bash
./scripts/stop-local.sh
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| LocalStack | http://localhost:4566 | AWS services |
| LocalStack UI | http://localhost:8055 | Web interface |
| Elasticsearch | http://localhost:9200 | Vector database |
| Mock LLM | http://localhost:8080 | LLM endpoint |
| Mock Embeddings | http://localhost:8081 | Embedding endpoint |

## Common Commands

### AWS Services

```bash
# List S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# List DynamoDB tables
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# List Lambda functions
aws --endpoint-url=http://localhost:4566 lambda list-functions

# List secrets
aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets

# Query DynamoDB
aws --endpoint-url=http://localhost:4566 dynamodb scan \
    --table-name codehealer-incidents

# Get secret value
aws --endpoint-url=http://localhost:4566 secretsmanager get-secret-value \
    --secret-id codehealer/local/github-token
```

### Elasticsearch

```bash
# Cluster health
curl http://localhost:9200/_cluster/health?pretty

# List indices
curl http://localhost:9200/_cat/indices?v

# Create index
curl -X PUT http://localhost:9200/code_fixes

# Search index
curl -X GET http://localhost:9200/code_fixes/_search?pretty
```

### Mock SageMaker

```bash
# Test LLM endpoint
curl -X POST http://localhost:8080/invocations \
    -H "Content-Type: application/json" \
    -d '{"inputs": "Fix this error: connection timeout"}'

# Test embedding endpoint
curl -X POST http://localhost:8081/invocations \
    -H "Content-Type: application/json" \
    -d '{"inputs": ["test text 1", "test text 2"]}'
```

## Troubleshooting

### Services won't start

```bash
# Clean up and restart
docker-compose -f docker-compose.localstack.yml down -v
docker system prune -f
./scripts/start-local.sh
```

### Port conflicts

```bash
# Check what's using ports
lsof -i :4566  # LocalStack
lsof -i :9200  # Elasticsearch
lsof -i :8080  # Mock LLM
lsof -i :8081  # Mock Embeddings

# Kill processes if needed
kill -9 <PID>
```

### Terraform errors

```bash
# Reset Terraform
cd terraform
rm -rf .terraform terraform-local.tfstate*
terraform init -reconfigure
```

### Lambda not working

```bash
# Check Lambda logs
aws --endpoint-url=http://localhost:4566 logs tail \
    /aws/lambda/codehealer-handler --follow

# Check if function exists
aws --endpoint-url=http://localhost:4566 lambda get-function \
    --function-name codehealer-handler

# Rebuild Lambda package
cd terraform
terraform taint module.lambda.aws_lambda_function.codehealer
terraform apply -var-file="environments/local.tfvars"
```

### Elasticsearch connection issues

```bash
# Check if Elasticsearch is healthy
curl http://localhost:9200/_cluster/health

# View Elasticsearch logs
docker-compose -f docker-compose.localstack.yml logs elasticsearch

# Restart Elasticsearch
docker-compose -f docker-compose.localstack.yml restart elasticsearch
```

## Development Workflow

### Making Code Changes

1. **Edit Lambda code** in `src/`
2. **Redeploy Lambda:**
   ```bash
   cd terraform
   terraform apply -var-file="environments/local.tfvars" -auto-approve
   ```
3. **Test immediately:**
   ```bash
   aws --endpoint-url=http://localhost:4566 lambda invoke \
       --function-name codehealer-handler \
       --payload file://test-payload.json \
       output.json
   ```

### Testing Different Scenarios

Create test payloads in `test-payloads/` directory:

**test-payloads/github-failure.json:**
```json
{
  "body": "{\"workflow_run\": {\"id\": 12345, \"status\": \"completed\", \"conclusion\": \"failure\", \"name\": \"CI\", \"head_branch\": \"main\"}, \"repository\": {\"name\": \"test-repo\", \"full_name\": \"org/test-repo\", \"owner\": {\"login\": \"org\"}}}"
}
```

**test-payloads/argocd-degraded.json:**
```json
{
  "body": "{\"application\": {\"metadata\": {\"name\": \"myapp\"}, \"status\": {\"health\": {\"status\": \"Degraded\"}, \"sync\": {\"status\": \"Synced\"}}}}"
}
```

Test with:
```bash
aws --endpoint-url=http://localhost:4566 lambda invoke \
    --function-name codehealer-handler \
    --payload file://test-payloads/github-failure.json \
    output.json
```

### Debugging Tips

1. **Enable verbose logging:**
   ```bash
   # Add to terraform/environments/local.tfvars
   lambda_additional_env_vars = {
     LOG_LEVEL = "DEBUG"
   }
   ```

2. **Watch Lambda logs in real-time:**
   ```bash
   aws --endpoint-url=http://localhost:4566 logs tail \
       /aws/lambda/codehealer-handler --follow
   ```

3. **Check DynamoDB for stored incidents:**
   ```bash
   aws --endpoint-url=http://localhost:4566 dynamodb scan \
       --table-name codehealer-incidents \
       --output json | jq
   ```

## Environment Configuration

### Local Environment Variables

Set these in `terraform/environments/local.tfvars`:

```hcl
environment = "local"

# Network (mock values for LocalStack)
vpc_id     = "vpc-local"
subnet_ids = ["subnet-local-1", "subnet-local-2"]

# Lambda settings (minimal for local)
lambda_memory_size = 512
lambda_timeout     = 60
lambda_reserved_concurrent_executions = 10

# DynamoDB
dynamodb_billing_mode = "PAY_PER_REQUEST"

# Logging (short retention for local)
log_retention_days = 1

# Features
auto_fix_enabled = "false"
enable_xray = false
create_sns_topic = true

# OpenSearch (settings ignored in local mode)
opensearch_allowed_cidr_blocks = ["0.0.0.0/0"]
opensearch_instance_type           = "t3.small.search"
opensearch_instance_count          = 1
opensearch_dedicated_master_enabled = false
opensearch_zone_awareness_enabled  = false
opensearch_volume_size             = 10

# SageMaker (settings ignored in local mode)
sagemaker_llm_instance_type              = "ml.mock.small"
sagemaker_llm_instance_count             = 1
sagemaker_embedding_instance_type        = "ml.mock.small"
sagemaker_embedding_instance_count       = 1
sagemaker_enable_autoscaling             = false

# Mock secrets
github_token          = "mock-github-token"
github_webhook_secret = "mock-webhook-secret"
slack_token           = "mock-slack-token"
openai_api_key        = "mock-openai-key"

# Configuration
github_repo         = "test-org/test-repo"
slack_channel_id    = "C0000000000"
slack_senior_dev_id = "U0000000000"
llm_provider        = "openai"
```

## Data Persistence

LocalStack persists data in `./localstack-data/` directory:
- S3 buckets
- DynamoDB tables
- Secrets Manager secrets

**To start fresh:**
```bash
rm -rf localstack-data/
./scripts/start-local.sh
```

**To preserve data between restarts:**
- Don't delete `localstack-data/`
- Services will restore previous state

## CI/CD Integration

### Running Tests in CI

```yaml
# .github/workflows/test-local.yml
name: Local Integration Tests

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start LocalStack
        run: ./scripts/start-local.sh
      
      - name: Run Tests
        run: ./scripts/test-local.sh
      
      - name: Stop LocalStack
        run: ./scripts/stop-local.sh
```

## Performance Tips

1. **Faster Lambda redeployment:**
   ```bash
   # Only update Lambda code without full terraform apply
   cd terraform
   terraform apply -target=module.lambda -var-file="environments/local.tfvars"
   ```

2. **Skip unnecessary services:**
   ```bash
   # Only start what you need
   docker-compose -f docker-compose.localstack.yml up -d localstack mock-sagemaker
   ```

3. **Reduce log noise:**
   ```bash
   # Set LOG_LEVEL=ERROR in local.tfvars
   ```

## Clean Up

### Soft cleanup (keep data)
```bash
./scripts/stop-local.sh
```

### Full cleanup (remove all data)
```bash
# Stop services and remove volumes
./scripts/stop-local.sh

# Remove all local data
rm -rf localstack-data/
rm -rf terraform/terraform-local.tfstate*
rm -rf terraform/.terraform/

# Clean Docker
docker system prune -f
```

## Additional Resources

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS CLI with LocalStack](https://docs.localstack.cloud/user-guide/integrations/aws-cli/)

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Address already in use" | Kill process using the port: `lsof -ti:4566 \| xargs kill -9` |
| "Connection refused" | Wait for services to start: `sleep 10` after docker-compose up |
| Terraform state locked | Remove lock: `rm -rf terraform/.terraform.lock.hcl` |
| Lambda timeout | Increase timeout in `local.tfvars`: `lambda_timeout = 120` |
| Out of memory | Increase Docker memory limit in Docker Desktop settings |

## Getting Help

1. Check logs: `docker-compose -f docker-compose.localstack.yml logs`
2. Verify services: `./scripts/test-local.sh`
3. Check Terraform: `terraform validate`
4. Review configuration: `cat terraform/environments/local.tfvars`

---

**Happy Local Development! 🚀**
