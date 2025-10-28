#!/bin/bash

set -e

echo "🚀 Starting CodeHealer Local Development Environment"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Use docker compose (v2 syntax)
DOCKER_COMPOSE="docker compose"

# Verify docker compose works
if ! $DOCKER_COMPOSE version > /dev/null 2>&1; then
    echo -e "${RED}❌ 'docker compose' command not found. Please install Docker Compose v2.${NC}"
    exit 1
fi

echo "Using: $DOCKER_COMPOSE"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Start services
echo -e "${GREEN}📦 Starting LocalStack and mock services...${NC}"
$DOCKER_COMPOSE -f compose.localstack.yml up -d --build

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Check LocalStack
echo "Checking LocalStack..."
MAX_RETRIES=30
RETRY_COUNT=0
until curl -s http://localhost:4566/_localstack/health 2>/dev/null | grep -q '"services":'; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ LocalStack failed to start${NC}"
        $DOCKER_COMPOSE -f compose.localstack.yml logs localstack
        exit 1
    fi
    echo "Waiting for LocalStack... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done
echo -e "${GREEN}✅ LocalStack is ready${NC}"

# Check Elasticsearch
echo "Checking Elasticsearch..."
RETRY_COUNT=0
until curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Elasticsearch failed to start${NC}"
        $DOCKER_COMPOSE -f compose.localstack.yml logs elasticsearch
        exit 1
    fi
    echo "Waiting for Elasticsearch... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done
echo -e "${GREEN}✅ Elasticsearch is ready${NC}"

# Check Mock SageMaker
echo "Checking Mock SageMaker..."
RETRY_COUNT=0
until curl -s http://localhost:8080/health > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Mock SageMaker failed to start${NC}"
        $DOCKER_COMPOSE -f compose.localstack.yml logs mock-sagemaker
        exit 1
    fi
    echo "Waiting for Mock SageMaker... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done
echo -e "${GREEN}✅ Mock SageMaker is ready${NC}"

# Initialize Terraform
echo -e "${GREEN}🔧 Initializing Terraform...${NC}"
cd terraform

# Create local backend override
cat > backend-override.tf << 'EOF'
terraform {
  backend "local" {
    path = "terraform-local.tfstate"
  }
}
EOF

# Create provider override if it doesn't exist
if [ ! -f provider-override.tf ]; then
    if [ -f provider-override.tf.example ]; then
        cp provider-override.tf.example provider-override.tf
    fi
fi

terraform init -reconfigure

# Plan infrastructure
echo -e "${GREEN}📋 Planning infrastructure...${NC}"
terraform plan \
    -var-file="environments/local.tfvars" \
    -out=tfplan-local

# Check if running in CI (non-interactive)
if [ -z "$CI" ]; then
    # Interactive mode - ask for confirmation
    echo -e "${YELLOW}🏗️  Applying infrastructure...${NC}"
    read -p "Apply changes? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        terraform apply tfplan-local
    else
        echo "Aborted."
        exit 0
    fi
else
    # CI mode - auto-approve
    echo -e "${YELLOW}🏗️  Applying infrastructure (CI mode - auto-approve)...${NC}"
    terraform apply -auto-approve tfplan-local
fi

echo ""
echo -e "${GREEN}✅ Local environment is ready!${NC}"
echo ""
echo "📊 Services:"
echo "  - LocalStack:        http://localhost:4566"
echo "  - Elasticsearch:     http://localhost:9200"
echo "  - Mock LLM:          http://localhost:8080"
echo "  - Mock Embeddings:   http://localhost:8081"
echo ""
echo "🔍 To view logs:"
echo "  $DOCKER_COMPOSE -f compose.localstack.yml logs -f"
echo ""
echo "🛑 To stop:"
echo "  ./scripts/stop-local.sh"
