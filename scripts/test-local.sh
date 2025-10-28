#!/bin/bash

echo "🧪 Testing Local Environment"

# Test LocalStack services
echo "Testing S3..."
aws --endpoint-url=http://localhost:4566 s3 ls

echo "Testing DynamoDB..."
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

echo "Testing Secrets Manager..."
aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets

echo "Testing Mock SageMaker..."
curl -X POST http://localhost:8080/invocations \
    -H "Content-Type: application/json" \
    -d '{"inputs": "test error message"}'

echo ""
echo "Testing Elasticsearch..."
curl http://localhost:9200/_cluster/health?pretty

echo ""
echo "✅ All tests completed"
