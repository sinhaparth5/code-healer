# Override for local development with LocalStack
# Rename to provider-override.tf to activate

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Use local backend instead of S3
  backend "local" {
    path = "terraform-local.tfstate"
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    apigateway     = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    dynamodb       = "http://localhost:4566"
    ec2            = "http://localhost:4566"
    es             = "http://localhost:4566"
    iam            = "http://localhost:4566"
    kms            = "http://localhost:4566"
    lambda         = "http://localhost:4566"
    s3             = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
    sns            = "http://localhost:4566"
    sqs            = "http://localhost:4566"
    sts            = "http://localhost:4566"
    cloudwatchlogs = "http://localhost:4566"
  }
}
