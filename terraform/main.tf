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
  lamdba_function_name = module.lambda.lambda_function_name
  
  # Loggin configuration
  log_retention_days = var.environment == "prod" ? 30 : 7
  api_logging_level = var.environment == "prod" ? "INFO" : "ERROR"
  enable_data_trace = var.environment != "prod"
  enable_xray_tracing = true

  # Performance and throttling
  throttling_burst_limit = var.throttling_burst_limit
  throttling_rate_limit = var.throttling_rate_limit

  # Security - WAF 
  enable_waf = var.enable_waf
  waf_rate_limit = var.waf_rate_limit
  allowed_countries = var.allowed_countries

  # Custom domian
  custom_domain_name = var.custom_domain_name
  certificate_arn = var.custom_domain_name != "" ? aws_acm_certificate.webhook[0].arn : ""

  # Monitoring
  error_threshold = var.error_threshold
  latency_threshold = var.latency_threshold
  alarm_sns_topic_arn = aws_sns_topic.alerts.arn

  tags = local.common_tags

  depends_on = [
    module.lambda
  ]
}
