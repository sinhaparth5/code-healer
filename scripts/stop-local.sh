#!/bin/bash

set -e

echo "­ƒÜÇ Starting CodeHealer Local Development Environment"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ÔØî Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
echo -e "${GREEN}­ƒôª Starting LocalStack and mock services...${NC}"
docker-compose -f docker-compose.localstack.yml up -d

# Wait for services to be healthy
echo -e "${YELLOW}ÔÅ│ Waiting for services to be ready...${NC}"
sleep 10

# Check LocalStack
echo "Checking LocalStack..."
until curl -s http://localhost:4566/_localstack/health | grep -q '"services":'; do
    echo "Waiting for LocalStack..."
    sleep 2
done
echo -e "${GREEN}Ô£à LocalStack is ready${NC}"

# Check Elasticsearch
echo "Checking Elasticsearch..."
until curl -s http://localhost:9200/_cluster/health > /dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 2
done
echo -e "${GREEN}Ô£à Elasticsearch is ready${NC}"

# Check Mock SageMaker
echo "Checking Mock SageMaker..."
until curl -s http://localhost:8080/health > /dev/null; do
    echo "Waiting for Mock SageMaker..."
    sleep 2
done
echo -e "${GREEN}Ô£à Mock SageMaker is ready${NC}"

# Initialize Terraform
echo -e "${GREEN}­ƒöº Initializing Terraform...${NC}"
cd terraform

# Create local backend override
cat > backend-override.tf << 'EOF'
terraform {
  backend "local" {
    path = "terraform-local.tfstate"
  }
}
EOF

# Create provider override
cp provider-override.tf.example provider-override.tf 2>/dev/null || true

terraform init -reconfigure

# Plan infrastructure
echo -e "${GREEN}­ƒôï Planning infrastructure...${NC}"
terraform plan \
    -var-file="environments/local.tfvars" \
    -out=tfplan-local

# Apply infrastructure
echo -e "${YELLOW}­ƒÅù´©Å  Applying infrastructure...${NC}"
read -p "Apply changes? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
    terraform apply tfplan-local
    
    echo ""
    echo -e "${GREEN}Ô£à Local environment is ready!${NC}"
    echo ""
    echo "­ƒôè Services:"
    echo "  - LocalStack:        http://localhost:4566"
    echo "  - LocalStack UI:     http://localhost:8055"
    echo "  - Elasticsearch:     http://localhost:9200"
    echo "  - Mock LLM:          http://localhost:8080"
    echo "  - Mock Embeddings:   http://localhost:8081"
    echo ""
    echo "­ƒöì To view logs:"
    echo "  docker-compose -f docker-compose.localstack.yml logs -f"
    echo ""
    echo "­ƒøæ To stop:"
    echo "  ./scripts/stop-local.sh"
else
    echo "Aborted."
fi

