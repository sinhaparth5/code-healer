#!/bin/bash

set -e

echo "🛑 Stopping CodeHealer Local Environment"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Use docker compose (v2 syntax)
DOCKER_COMPOSE="docker compose"

# Verify docker compose works
if ! $DOCKER_COMPOSE version > /dev/null 2>&1; then
    echo -e "${RED}❌ 'docker compose' command not found.${NC}"
    exit 1
fi

echo "Using: $DOCKER_COMPOSE"

# Destroy Terraform resources
if [ -d "terraform" ]; then
    echo "Destroying Terraform resources..."
    cd terraform
    if [ -f "terraform-local.tfstate" ]; then
        terraform destroy -var-file="environments/local.tfvars" -auto-approve || true
    fi
    cd ..
fi

# Stop Docker services
echo "Stopping Docker services..."
$DOCKER_COMPOSE -f compose.localstack.yml down -v

echo -e "${GREEN}✅ Local environment stopped${NC}"
