#!/bin/bash
set -e

echo "================================================"
echo "DevFlowFix Complete AWS Deployment"
echo "================================================"

# ============================================
# CONFIGURATION
# ============================================

export PROJECT_NAME="devflowfix"
export AWS_REGION="us-east-1"
export ENVIRONMENT="dev"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# ============================================
# STEP 1: CREATE S3 BUCKETS
# ============================================

echo "Step 1: Creating S3 Buckets..."

aws s3 mb s3://${PROJECT_NAME}-deployment-${AWS_ACCOUNT_ID} --region ${AWS_REGION} 2>/dev/null || echo "Deployment bucket already exists"
aws s3 mb s3://${PROJECT_NAME}-model-artifacts-${AWS_ACCOUNT_ID} --region ${AWS_REGION} 2>/dev/null || echo "Model artifacts bucket already exists"
aws s3 mb s3://${PROJECT_NAME}-data-capture-${AWS_ACCOUNT_ID} --region ${AWS_REGION} 2>/dev/null || echo "Data capture bucket already exists"

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ${PROJECT_NAME}-deployment-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled 2>/dev/null || true

# Block public access
for bucket in deployment model-artifacts data-capture; do
  aws s3api put-public-access-block \
    --bucket ${PROJECT_NAME}-${bucket}-${AWS_ACCOUNT_ID} \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" 2>/dev/null || true
done

# Enable encryption
for bucket in deployment model-artifacts data-capture; do
  aws s3api put-bucket-encryption \
    --bucket ${PROJECT_NAME}-${bucket}-${AWS_ACCOUNT_ID} \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' 2>/dev/null || true
done

echo "✅ S3 Buckets created"
echo ""

# ============================================
# STEP 2: CREATE SECRETS MANAGER SECRETS
# ============================================

echo "Step 2: Creating Secrets Manager secrets..."

# Function to create or update secret
create_or_update_secret() {
  local secret_name=$1
  local secret_value=$2
  local description=$3
  
  if aws secretsmanager describe-secret --secret-id "$secret_name" --region ${AWS_REGION} 2>/dev/null; then
    echo "Secret $secret_name already exists, updating..."
    aws secretsmanager put-secret-value \
      --secret-id "$secret_name" \
      --secret-string "$secret_value" \
      --region ${AWS_REGION} >/dev/null
  else
    echo "Creating secret $secret_name..."
    aws secretsmanager create-secret \
      --name "$secret_name" \
      --description "$description" \
      --secret-string "$secret_value" \
      --region ${AWS_REGION} >/dev/null
  fi
}

# Create secrets (REPLACE WITH YOUR ACTUAL VALUES)
read -p "Enter GitHub Token (or press enter to use placeholder): " GITHUB_TOKEN
GITHUB_TOKEN=${GITHUB_TOKEN:-""}

read -p "Enter GitHub Webhook Secret (or press enter to use placeholder): " WEBHOOK_SECRET
WEBHOOK_SECRET=${WEBHOOK_SECRET:-"YOUR_WEBHOOK_SECRET_HERE"}

read -p "Enter Slack Token (or press enter to use placeholder): " SLACK_TOKEN
SLACK_TOKEN=${SLACK_TOKEN:-"YOUR_SLACK_TOKEN_HERE"}

read -p "Enter NVIDIA API Key (or press enter to use placeholder): " NVIDIA_KEY
NVIDIA_KEY=${NVIDIA_KEY:-""}

read -p "Enter OpenAI API Key (or press enter to use placeholder): " OPENAI_KEY
OPENAI_KEY=${OPENAI_KEY:-"YOUR_OPENAI_KEY_HERE"}

read -p "Enter GitHub Repo (format: owner/repo): " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-"sinhaparth5/code-healer-test-app"}

read -p "Enter Slack Channel ID: " SLACK_CHANNEL
SLACK_CHANNEL=${SLACK_CHANNEL:-"C0000000000"}

create_or_update_secret \
  "${PROJECT_NAME}/${ENVIRONMENT}/github-token" \
  "$GITHUB_TOKEN" \
  "GitHub API token for DevFlowFix"

create_or_update_secret \
  "${PROJECT_NAME}/${ENVIRONMENT}/github-webhook-secret" \
  "$WEBHOOK_SECRET" \
  "GitHub webhook secret"

create_or_update_secret \
  "${PROJECT_NAME}/${ENVIRONMENT}/slack-token" \
  "$SLACK_TOKEN" \
  "Slack API token"

create_or_update_secret \
  "${PROJECT_NAME}/${ENVIRONMENT}/nvidia-nim-api-key" \
  "$NVIDIA_KEY" \
  "NVIDIA NIM API key"

create_or_update_secret \
  "${PROJECT_NAME}/${ENVIRONMENT}/openai-api-key" \
  "$OPENAI_KEY" \
  "OpenAI API key"

create_or_update_secret \
  "${PROJECT_NAME}/${ENVIRONMENT}/app-config" \
  "{
    \"github\": {\"repo\": \"$GITHUB_REPO\", \"branch\": \"main\"},
    \"slack\": {\"channel_id\": \"$SLACK_CHANNEL\", \"senior_dev_id\": \"U0000000000\"},
    \"llm\": {
      \"provider\": \"nvidia_nim\",
      \"model\": \"nvidia/llama-3.1-nemotron-nano-vl-8b-v1\",
      \"max_tokens\": 2048,
      \"temperature\": 0.1
    },
    \"nvidia_nim\": {
      \"endpoint\": \"https://integrate.api.nvidia.com/v1\",
      \"model\": \"nvidia/llama-3.1-nemotron-nano-vl-8b-v1\"
    }
  }" \
  "Application configuration"

echo "✅ Secrets created"
echo ""

# ============================================
# STEP 3: CREATE IAM ROLES
# ============================================

echo "Step 3: Creating IAM roles..."

# Lambda execution role trust policy
cat > /tmp/lambda-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create Lambda execution role
if aws iam get-role --role-name ${PROJECT_NAME}-lambda-execution 2>/dev/null; then
  echo "Lambda execution role already exists"
else
  aws iam create-role \
    --role-name ${PROJECT_NAME}-lambda-execution \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --description "Lambda execution role for CodeHealer"
fi

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name ${PROJECT_NAME}-lambda-execution \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

# Create Lambda permissions policy
cat > /tmp/lambda-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:${PROJECT_NAME}/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::${PROJECT_NAME}-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:InvokeEndpoint"
      ],
      "Resource": "arn:aws:sagemaker:${AWS_REGION}:${AWS_ACCOUNT_ID}:endpoint/${PROJECT_NAME}-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/lambda/${PROJECT_NAME}-*:*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ${PROJECT_NAME}-lambda-execution \
  --policy-name ${PROJECT_NAME}-lambda-permissions \
  --policy-document file:///tmp/lambda-policy.json

export LAMBDA_ROLE_ARN=$(aws iam get-role --role-name ${PROJECT_NAME}-lambda-execution --query 'Role.Arn' --output text)

# SageMaker execution role trust policy
cat > /tmp/sagemaker-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "sagemaker.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create SageMaker execution role
if aws iam get-role --role-name ${PROJECT_NAME}-sagemaker-execution 2>/dev/null; then
  echo "SageMaker execution role already exists"
else
  aws iam create-role \
    --role-name ${PROJECT_NAME}-sagemaker-execution \
    --assume-role-policy-document file:///tmp/sagemaker-trust-policy.json \
    --description "SageMaker execution role for CodeHealer"
fi

# Create SageMaker permissions policy
cat > /tmp/sagemaker-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${PROJECT_NAME}-*",
        "arn:aws:s3:::${PROJECT_NAME}-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:CreateLogGroup"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ${PROJECT_NAME}-sagemaker-execution \
  --policy-name ${PROJECT_NAME}-sagemaker-permissions \
  --policy-document file:///tmp/sagemaker-policy.json

export SAGEMAKER_ROLE_ARN=$(aws iam get-role --role-name ${PROJECT_NAME}-sagemaker-execution --query 'Role.Arn' --output text)

# API Gateway roles
cat > /tmp/apigateway-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "apigateway.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

if aws iam get-role --role-name ${PROJECT_NAME}-apigateway-cloudwatch 2>/dev/null; then
  echo "API Gateway CloudWatch role already exists"
else
  aws iam create-role \
    --role-name ${PROJECT_NAME}-apigateway-cloudwatch \
    --assume-role-policy-document file:///tmp/apigateway-trust-policy.json \
    --description "API Gateway CloudWatch logs role"
  
  aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-apigateway-cloudwatch \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs
fi

export CLOUDWATCH_ROLE_ARN=$(aws iam get-role --role-name ${PROJECT_NAME}-apigateway-cloudwatch --query 'Role.Arn' --output text)

echo "✅ IAM roles created"
echo "Waiting 10 seconds for IAM roles to propagate..."
sleep 10
echo ""
# ============================================
# STEP 4: PACKAGE AND DEPLOY LAMBDA
# ============================================

echo "Step 4: Packaging and deploying Lambda function..."

# Clean up previous builds
rm -rf deployment
rm -f lambda_package.zip

# Create deployment directory
mkdir -p deployment

# Copy source code
echo "📋 Copying source code from src/..."
cp -r src/* deployment/

# Navigate to deployment directory
cd deployment

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: requirements.txt not found in src/ directory!"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt \
    --target . \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    --quiet

# Remove unnecessary files to reduce size
echo "🧹 Removing unnecessary files..."
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Create zip file
echo "🗜️  Creating ZIP package..."
zip -r9 ../lambda_package.zip . \
    -x "*.git*" \
    -x "*.pyc" \
    -x "*__pycache__*" \
    -x "*.DS_Store" \
    -x "*.gitignore" \
    2>/dev/null

cd ..

# Get file size
SIZE=$(du -h lambda_package.zip | cut -f1)
SIZE_BYTES=$(stat -f%z lambda_package.zip 2>/dev/null || stat -c%s lambda_package.zip 2>/dev/null)

echo "📦 Package size: $SIZE"

# Create or update Lambda function
if aws lambda get-function --function-name ${PROJECT_NAME}-handler --region ${AWS_REGION} 2>/dev/null; then
  echo "Lambda handler already exists, updating code..."
 
  if [ $SIZE_BYTES -gt 52428800 ]; then
    echo "📤 Uploading to S3 (package > 50MB)..."
    aws s3 cp lambda_package.zip s3://${PROJECT_NAME}-deployment-${AWS_ACCOUNT_ID}/lambda_package.zip --region ${AWS_REGION}
   
    aws lambda update-function-code \
      --function-name ${PROJECT_NAME}-handler \
      --s3-bucket ${PROJECT_NAME}-deployment-${AWS_ACCOUNT_ID} \
      --s3-key lambda_package.zip \
      --region ${AWS_REGION} >/dev/null
  else
    aws lambda update-function-code \
      --function-name ${PROJECT_NAME}-handler \
      --zip-file fileb://lambda_package.zip \
      --region ${AWS_REGION} >/dev/null
  fi
 
  # Wait for the code update to complete
  echo "⏳ Waiting for code update to complete..."
  aws lambda wait function-updated --function-name ${PROJECT_NAME}-handler --region ${AWS_REGION} 2>/dev/null || {
    echo "   Using manual wait..."
    sleep 10
    MAX_ATTEMPTS=60
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
      STATE=$(aws lambda get-function --function-name ${PROJECT_NAME}-handler --region ${AWS_REGION} --query 'Configuration.State' --output text 2>/dev/null)
      LAST_UPDATE_STATUS=$(aws lambda get-function --function-name ${PROJECT_NAME}-handler --region ${AWS_REGION} --query 'Configuration.LastUpdateStatus' --output text 2>/dev/null)
     
      if [ "$STATE" = "Active" ] && [ "$LAST_UPDATE_STATUS" = "Successful" ]; then
        echo "   ✅ Code update completed"
        break
      fi
     
      if [ "$LAST_UPDATE_STATUS" = "Failed" ]; then
        echo "   ❌ Code update failed"
        exit 1
      fi
     
      echo "   State: $STATE, Status: $LAST_UPDATE_STATUS (attempt $((ATTEMPT+1))/$MAX_ATTEMPTS)"
      sleep 5
      ATTEMPT=$((ATTEMPT+1))
    done
   
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
      echo "   ❌ Timeout waiting for code update"
      exit 1
    fi
  }
 
else
  echo "Creating Lambda handler..."
 
  if [ $SIZE_BYTES -gt 52428800 ]; then
    echo "📤 Uploading to S3 (package > 50MB)..."
    aws s3 cp lambda_package.zip s3://${PROJECT_NAME}-deployment-${AWS_ACCOUNT_ID}/lambda_package.zip --region ${AWS_REGION}
   
    aws lambda create-function \
      --function-name ${PROJECT_NAME}-handler \
      --runtime python3.11 \
      --role ${LAMBDA_ROLE_ARN} \
      --handler lambda_handler.lambda_handler \
      --code S3Bucket=${PROJECT_NAME}-deployment-${AWS_ACCOUNT_ID},S3Key=lambda_package.zip \
      --timeout 300 \
      --memory-size 1024 \
      --region ${AWS_REGION} >/dev/null
  else
    aws lambda create-function \
      --function-name ${PROJECT_NAME}-handler \
      --runtime python3.11 \
      --role ${LAMBDA_ROLE_ARN} \
      --handler lambda_handler.lambda_handler \
      --zip-file fileb://lambda_package.zip \
      --timeout 300 \
      --memory-size 1024 \
      --region ${AWS_REGION} >/dev/null
  fi
 
  # Wait for function to be created
  echo "⏳ Waiting for Lambda function to be created..."
  aws lambda wait function-active --function-name ${PROJECT_NAME}-handler --region ${AWS_REGION}
fi

# Update Lambda environment variables
echo "⚙️  Configuring Lambda environment variables..."

# Create environment variables JSON file
cat > /tmp/lambda-env.json <<EOF
{
  "Variables": {
    "ENVIRONMENT": "${ENVIRONMENT}",
    "PROJECT_NAME": "${PROJECT_NAME}",
    "LOG_LEVEL": "INFO",
    "GITHUB_TOKEN_SECRET_NAME": "${PROJECT_NAME}/${ENVIRONMENT}/github-token",
    "GITHUB_WEBHOOK_SECRET_NAME": "${PROJECT_NAME}/${ENVIRONMENT}/github-webhook-secret",
    "SLACK_TOKEN_SECRET_NAME": "${PROJECT_NAME}/${ENVIRONMENT}/slack-token",
    "NVIDIA_API_KEY_SECRET_NAME": "${PROJECT_NAME}/${ENVIRONMENT}/nvidia-nim-api-key",
    "OPENAI_API_KEY_SECRET_NAME": "${PROJECT_NAME}/${ENVIRONMENT}/openai-api-key",
    "APP_CONFIG_SECRET_NAME": "${PROJECT_NAME}/${ENVIRONMENT}/app-config",
    "CONFIDENCE_THRESHOLD_PROD": "0.92",
    "CONFIDENCE_THRESHOLD_STAGING": "0.85",
    "CONFIDENCE_THRESHOLD_DEV": "0.75",
    "CONFIDENCE_THRESHOLD_DEFAULT": "0.85",
    "VECTOR_SIMILARITY_THRESHOLD": "0.75",
    "VECTOR_MAX_RESULTS": "10",
    "SLACK_NOTIFICATION_CHANNEL": "alerts",
    "SLACK_SEARCH_CHANNELS": "devops,alerts,incidents",
    "SLACK_TIME_WINDOW_DAYS": "180",
    "SLACK_MAX_RESULTS": "20",
    "APPROVAL_PROD_ALWAYS": "true",
    "APPROVAL_HIGH_RISK": "true",
    "APPROVAL_LOW_CONF_THRESHOLD": "0.9"
  }
}
EOF

# Update Lambda with environment variables from file
aws lambda update-function-configuration \
  --function-name ${PROJECT_NAME}-handler \
  --environment file:///tmp/lambda-env.json \
  --region ${AWS_REGION} >/dev/null

echo "✅ Lambda environment variables configured"

# Wait for configuration update to complete
echo "⏳ Waiting for configuration update to complete..."
sleep 5

export LAMBDA_ARN=$(aws lambda get-function --function-name ${PROJECT_NAME}-handler --query 'Configuration.FunctionArn' --output text --region ${AWS_REGION})

echo "✅ Lambda function deployed"
echo ""

# ============================================
# STEP 5: CREATE SAGEMAKER ENDPOINTS
# ============================================

echo "Step 5: Creating SageMaker endpoints..."
echo "⚠️  This will create GPU instances and may take 10-15 minutes"
read -p "Do you want to create SageMaker endpoints? (y/n): " CREATE_SAGEMAKER

if [ "$CREATE_SAGEMAKER" = "y" ] || [ "$CREATE_SAGEMAKER" = "Y" ]; then

  # LLM Model
  LLM_MODEL_NAME="${PROJECT_NAME}-llm-model"
  if aws sagemaker describe-model --model-name ${LLM_MODEL_NAME} --region ${AWS_REGION} 2>/dev/null; then
    echo "LLM model already exists"
  else
    echo "Creating LLM model..."
    aws sagemaker create-model \
      --model-name ${LLM_MODEL_NAME} \
      --primary-container '{
        "Image": "763104351884.dkr.ecr.'${AWS_REGION}'.amazonaws.com/huggingface-pytorch-inference:2.0.0-transformers4.28.1-gpu-py310-cu118-ubuntu20.04",
        "Environment": {
          "HF_MODEL_ID": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
          "HF_TASK": "text-generation"
        }
      }' \
      --execution-role-arn ${SAGEMAKER_ROLE_ARN} \
      --region ${AWS_REGION} >/dev/null
  fi

  # Embedding Model
  EMBEDDING_MODEL_NAME="${PROJECT_NAME}-embedding-model"
  if aws sagemaker describe-model --model-name ${EMBEDDING_MODEL_NAME} --region ${AWS_REGION} 2>/dev/null; then
    echo "Embedding model already exists"
  else
    echo "Creating embedding model..."
    aws sagemaker create-model \
      --model-name ${EMBEDDING_MODEL_NAME} \
      --primary-container '{
        "Image": "763104351884.dkr.ecr.'${AWS_REGION}'.amazonaws.com/huggingface-pytorch-inference:2.0.0-transformers4.28.1-gpu-py310-cu118-ubuntu20.04",
        "Environment": {
          "HF_MODEL_ID": "sentence-transformers/all-MiniLM-L6-v2",
          "HF_TASK": "feature-extraction"
        }
      }' \
      --execution-role-arn ${SAGEMAKER_ROLE_ARN} \
      --region ${AWS_REGION} >/dev/null
  fi

  # LLM Endpoint Configuration
  LLM_CONFIG_NAME="${PROJECT_NAME}-llm-config-$(date +%s)"
  echo "Creating LLM endpoint config..."
  aws sagemaker create-endpoint-config \
    --endpoint-config-name ${LLM_CONFIG_NAME} \
    --production-variants '[{
      "VariantName": "AllTraffic",
      "ModelName": "'${LLM_MODEL_NAME}'",
      "InitialInstanceCount": 1,
      "InstanceType": "ml.g5.xlarge",
      "InitialVariantWeight": 1
    }]' \
    --region ${AWS_REGION} >/dev/null

  # Embedding Endpoint Configuration
  EMBEDDING_CONFIG_NAME="${PROJECT_NAME}-embedding-config-$(date +%s)"
  echo "Creating embedding endpoint config..."
  aws sagemaker create-endpoint-config \
    --endpoint-config-name ${EMBEDDING_CONFIG_NAME} \
    --production-variants '[{
      "VariantName": "AllTraffic",
      "ModelName": "'${EMBEDDING_MODEL_NAME}'",
      "InitialInstanceCount": 1,
      "InstanceType": "ml.g5.xlarge",
      "InitialVariantWeight": 1
    }]' \
    --region ${AWS_REGION} >/dev/null

  # LLM Endpoint
  LLM_ENDPOINT_NAME="${PROJECT_NAME}-llm-endpoint"
  if aws sagemaker describe-endpoint --endpoint-name ${LLM_ENDPOINT_NAME} --region ${AWS_REGION} 2>/dev/null; then
    echo "Updating LLM endpoint..."
    aws sagemaker update-endpoint \
      --endpoint-name ${LLM_ENDPOINT_NAME} \
      --endpoint-config-name ${LLM_CONFIG_NAME} \
      --region ${AWS_REGION} >/dev/null
  else
    echo "Creating LLM endpoint (this will take ~10 minutes)..."
    aws sagemaker create-endpoint \
      --endpoint-name ${LLM_ENDPOINT_NAME} \
      --endpoint-config-name ${LLM_CONFIG_NAME} \
      --region ${AWS_REGION} >/dev/null
  fi

  # Embedding Endpoint
  EMBEDDING_ENDPOINT_NAME="${PROJECT_NAME}-embedding-endpoint"
  if aws sagemaker describe-endpoint --endpoint-name ${EMBEDDING_ENDPOINT_NAME} --region ${AWS_REGION} 2>/dev/null; then
    echo "Updating embedding endpoint..."
    aws sagemaker update-endpoint \
      --endpoint-name ${EMBEDDING_ENDPOINT_NAME} \
      --endpoint-config-name ${EMBEDDING_CONFIG_NAME} \
      --region ${AWS_REGION} >/dev/null
  else
    echo "Creating embedding endpoint (this will take ~10 minutes)..."
    aws sagemaker create-endpoint \
      --endpoint-name ${EMBEDDING_ENDPOINT_NAME} \
      --endpoint-config-name ${EMBEDDING_CONFIG_NAME} \
      --region ${AWS_REGION} >/dev/null
  fi

  echo "✅ SageMaker endpoints creation initiated"
  echo "⏳ Endpoints will be ready in ~10-15 minutes"
else
  echo "⏭️  Skipping SageMaker endpoint creation"
fi
echo ""

# ============================================
# STEP 6: CREATE API GATEWAY
# ============================================

echo "Step 6: Creating API Gateway..."

# Create REST API
if API_ID=$(aws apigateway get-rest-apis --query "items[?name=='${PROJECT_NAME}-api'].id" --output text --region ${AWS_REGION}) && [ -n "$API_ID" ]; then
  echo "API Gateway already exists: $API_ID"
else
  API_ID=$(aws apigateway create-rest-api \
    --name "${PROJECT_NAME}-api" \
    --description "CodeHealer webhook endpoint" \
    --endpoint-configuration types=REGIONAL \
    --region ${AWS_REGION} \
    --query 'id' \
    --output text)
  echo "Created API Gateway: $API_ID"
fi

export API_ID

# Get root resource
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id ${API_ID} \
  --region ${AWS_REGION} \
  --query 'items[0].id' \
  --output text)

# Create /webhook resource
WEBHOOK_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id ${API_ID} \
  --region ${AWS_REGION} \
  --query "items[?path=='/webhook'].id" \
  --output text)

if [ -z "$WEBHOOK_RESOURCE_ID" ]; then
  WEBHOOK_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id ${API_ID} \
    --parent-id ${ROOT_RESOURCE_ID} \
    --path-part webhook \
    --region ${AWS_REGION} \
    --query 'id' \
    --output text)
  echo "Created /webhook resource"
fi

# Create POST method (no authorizer for simplicity)
aws apigateway put-method \
  --rest-api-id ${API_ID} \
  --resource-id ${WEBHOOK_RESOURCE_ID} \
  --http-method POST \
  --authorization-type NONE \
  --region ${AWS_REGION} 2>/dev/null || echo "Method already exists"

# Set up Lambda integration
aws apigateway put-integration \
  --rest-api-id ${API_ID} \
  --resource-id ${WEBHOOK_RESOURCE_ID} \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations" \
  --region ${AWS_REGION} 2>/dev/null || echo "Integration already exists"

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name ${PROJECT_NAME}-handler \
  --statement-id apigateway-invoke-$(date +%s) \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" \
  --region ${AWS_REGION} 2>/dev/null || echo "Permission already exists"

# Deploy API
DEPLOYMENT_ID=$(aws apigateway create-deployment \
  --rest-api-id ${API_ID} \
  --stage-name ${ENVIRONMENT} \
  --stage-description "${ENVIRONMENT} stage" \
  --description "Deployment $(date)" \
  --region ${AWS_REGION} \
  --query 'id' \
  --output text)

# Set up CloudWatch logging
aws apigateway update-account \
  --patch-operations op=replace,path=/cloudwatchRoleArn,value=${CLOUDWATCH_ROLE_ARN} \
  --region ${AWS_REGION} 2>/dev/null || true

aws apigateway update-stage \
  --rest-api-id ${API_ID} \
  --stage-name ${ENVIRONMENT} \
  --patch-operations \
    op=replace,path=/logging/loglevel,value=INFO \
    op=replace,path=/metrics/enabled,value=true \
  --region ${AWS_REGION} 2>/dev/null || true

export WEBHOOK_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${ENVIRONMENT}/webhook"

echo "✅ API Gateway created"
echo ""

# ============================================
# FINAL OUTPUT
# ============================================

echo "================================================"
echo "🎉 DEPLOYMENT COMPLETE!"
echo "================================================"
echo ""
echo "🔗 Webhook URL:"
echo "   ${WEBHOOK_URL}"
echo ""
echo "📦 Resources Created:"
echo "   - S3 Buckets: 3"
echo "   - Secrets: 6"
echo "   - Lambda Function: ${PROJECT_NAME}-handler"
echo "   - API Gateway: ${API_ID}"
if [ "$CREATE_SAGEMAKER" = "y" ] || [ "$CREATE_SAGEMAKER" = "Y" ]; then
echo "   - SageMaker Endpoints: 2 (creating...)"
fi
echo ""
echo "🧪 Test your webhook:"
echo "   curl -X POST '${WEBHOOK_URL}' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -H 'X-GitHub-Event: ping' \\"
echo "     -d '{\"test\": \"webhook\"}'"
echo ""
echo "📊 Monitor Lambda logs:"
echo "   aws logs tail /aws/lambda/${PROJECT_NAME}-handler --follow --region ${AWS_REGION}"
echo ""
if [ "$CREATE_SAGEMAKER" = "y" ] || [ "$CREATE_SAGEMAKER" = "Y" ]; then
echo "🔍 Check SageMaker endpoints status:"
echo "   aws sagemaker describe-endpoint --endpoint-name ${PROJECT_NAME}-llm-endpoint --region ${AWS_REGION}"
echo "   aws sagemaker describe-endpoint --endpoint-name ${PROJECT_NAME}-embedding-endpoint --region ${AWS_REGION}"
echo ""
fi
echo "================================================"

# Save deployment info
cat > deployment-info.txt <<EOF
CodeHealer Deployment Information
==================================
Date: $(date)
AWS Account: ${AWS_ACCOUNT_ID}
Region: ${AWS_REGION}
Environment: ${ENVIRONMENT}

Webhook URL: ${WEBHOOK_URL}

Lambda Function: ${PROJECT_NAME}-handler
Handler: lambda_handler.lambda_handler

API Gateway ID: ${API_ID}

S3 Buckets:
  - s3://${PROJECT_NAME}-deployment-${AWS_ACCOUNT_ID}
  - s3://${PROJECT_NAME}-model-artifacts-${AWS_ACCOUNT_ID}
  - s3://${PROJECT_NAME}-data-capture-${AWS_ACCOUNT_ID}

Secrets (in AWS Secrets Manager):
  - ${PROJECT_NAME}/${ENVIRONMENT}/github-token
  - ${PROJECT_NAME}/${ENVIRONMENT}/github-webhook-secret
  - ${PROJECT_NAME}/${ENVIRONMENT}/slack-token
  - ${PROJECT_NAME}/${ENVIRONMENT}/nvidia-nim-api-key
  - ${PROJECT_NAME}/${ENVIRONMENT}/openai-api-key
  - ${PROJECT_NAME}/${ENVIRONMENT}/app-config

GitHub Webhook Configuration:
  Payload URL: ${WEBHOOK_URL}
  Content type: application/json
  Events: Issues, Pull requests, Workflow runs
EOF

if [ "$CREATE_SAGEMAKER" = "y" ] || [ "$CREATE_SAGEMAKER" = "Y" ]; then
cat >> deployment-info.txt <<EOF

SageMaker Endpoints:
  - LLM: ${PROJECT_NAME}-llm-endpoint
  - Embedding: ${PROJECT_NAME}-embedding-endpoint
EOF
fi

echo ""
echo "💾 Deployment info saved to: deployment-info.txt"
echo ""