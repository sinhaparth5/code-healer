# CodeHealer Main Terraform Configuration
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source = "hashicrop/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for state storage
  backend "s3" {
    bucket = "codehealer-terraform-state"
    key = "prod/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "codehealer-terraform-locks"
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project = "CodeHealer"
      Environment = var.environment
      ManagedBy = "Terraform"
      Owner = "DevOps"
    }
  }
}

# Local variable
locals {
  project_name = "codehealer"
  common_tags = {
    Project = "CodeHealer"
    Environment = var.environment
    Terraform = "true"
    Repository = "https://github.com/sinhaparth5/code-healer"
  }
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  project_name = local.project_name
  stage_name = var.environment
  lambda_invoke_arn    = module.lambda.lambda_invoke_arn
  lamdba_function_name = module.lambda_function_name
}
