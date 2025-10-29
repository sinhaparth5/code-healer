#!/bin/bash

set -e

echo "🧪 Testing Local Environment"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Use docker compose (v2 syntax)
DOCKER_COMPOSE="docker compose"

# Test LocalStack services
echo -e "${YELLOW}Testing LocalStack S3...${NC}"
if aws --endpoint-url=http://localhost:4566 s3 ls > /dev/null 2>&1; then
    echo -e "${GREEN}✅ S3 is working${NC}"
else
    echo -e "${RED}❌ S3 failed${NC}"
fi

echo -e "${YELLOW}Testing DynamoDB...${NC}"
if aws --endpoint-url=http://localhost:4566 dynamodb list-tables > /dev/null 2>&1; then
    echo -e "${GREEN}✅ DynamoDB is working${NC}"
    aws --endpoint-url=http://localhost:4566 dynamodb list-tables
else
    echo -e "${RED}❌ DynamoDB failed${NC}"
fi

echo -e "${YELLOW}Testing Secrets Manager...${NC}"
if aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Secrets Manager is working${NC}"
    aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets --query 'SecretList[].Name'
else
    echo -e "${RED}❌ Secrets Manager failed${NC}"
fi

# Test Mock SageMaker
echo -e "${YELLOW}Testing Mock SageMaker LLM...${NC}"
LLM_RESPONSE=$(curl -s -X POST http://localhost:8080/invocations \
    -H "Content-Type: application/json" \
    -d '{"inputs": "test error message"}' 2>/dev/null)

if echo "$LLM_RESPONSE" | grep -q "generated_text"; then
    echo -e "${GREEN}✅ Mock LLM is working${NC}"
    echo "$LLM_RESPONSE" | jq '.' 2>/dev/null || echo "$LLM_RESPONSE"
else
    echo -e "${RED}❌ Mock LLM failed${NC}"
    echo "Response: $LLM_RESPONSE"
fi

echo -e "${YELLOW}Testing Mock SageMaker Embeddings...${NC}"
EMB_RESPONSE=$(curl -s -X POST http://localhost:8081/invocations \
    -H "Content-Type: application/json" \
    -d '{"inputs": ["test text"]}' 2>/dev/null)

if echo "$EMB_RESPONSE" | grep -q "embeddings"; then
    echo -e "${GREEN}✅ Mock Embeddings is working${NC}"
    echo "$EMB_RESPONSE" | jq '.embeddings | length' 2>/dev/null || echo "Embeddings present"
else
    echo -e "${RED}❌ Mock Embeddings failed${NC}"
    echo "Response: $EMB_RESPONSE"
fi

# Test Elasticsearch
echo -e "${YELLOW}Testing Elasticsearch...${NC}"
ES_HEALTH=$(curl -s http://localhost:9200/_cluster/health 2>/dev/null)

if echo "$ES_HEALTH" | grep -q "status"; then
    echo -e "${GREEN}✅ Elasticsearch is working${NC}"
    echo "$ES_HEALTH" | jq '.' 2>/dev/null || echo "$ES_HEALTH"
else
    echo -e "${RED}❌ Elasticsearch failed${NC}"
fi

# Show running containers
echo ""
echo -e "${YELLOW}Running Containers:${NC}"
$DOCKER_COMPOSE -f compose.localstack.yml ps

echo ""
echo -e "${GREEN}✅ All tests completed${NC}"
