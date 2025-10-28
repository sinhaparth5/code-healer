#!/bin/bash

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
sleep 5

# Set AWS configuration for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
AWS_ENDPOINT="http://localhost:4566"

echo "Initializing LocalStack resources..."

# Create S3 buckets
echo "Creating S3 buckets..."
awslocal s3 mb s3://codehealer-deployment-000000000000 || true
awslocal s3 mb s3://codehealer-model-artifacts-000000000000 || true
awslocal s3 mb s3://codehealer-data-capture-000000000000 || true

# Create DynamoDB tables
echo "Creating DynamoDB tables..."
awslocal dynamodb create-table \
    --table-name codehealer-incidents \
    --attribute-definitions \
        AttributeName=incident_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=N \
    --key-schema \
        AttributeName=incident_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST || true

# Create Secrets
echo "Creating secrets..."
awslocal secretsmanager create-secret \
    --name codehealer/local/github-token \
    --secret-string "mock-github-token" || true

awslocal secretsmanager create-secret \
    --name codehealer/local/slack-token \
    --secret-string "mock-slack-token" || true

awslocal secretsmanager create-secret \
    --name codehealer/local/openai-api-key \
    --secret-string "mock-openai-key" || true

# Create SNS topic
echo "Creating SNS topic..."
awslocal sns create-topic --name codehealer-alerts || true

echo "LocalStack initialization complete!"
