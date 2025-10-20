# GENERAL CONFIGURATION
variable "aws_region" {
  description = "AWS region for all resources"
  type = string
  default = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type = string
  default = "prod"
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "alert_email" {
  description = "Email address for cloudwatch alarms"
  type = string
  default = ""
}

# API Gateway Configuration
variable "throttling_burst_limit" {
  description = "API Gateway throttling burst limit"
  type = number
  default = 100
}

variable "throttling_rate_limit" {
  description = "API Gateway throttling rate limit (requests per second)"
  type = number
  default = 50
}

variable "enable_waf" {
  description = "Enable AWS WAF for API Gateway"
  type = bool
  default = true
}

variable "waf_rate_limit" {
  description = "WAF rate limit (requests per 5 minutes from a single IP"
  type = number
  default = 2000
}

variable "allowed_countries" {
  description = "List of allowed country code (ISO 3166-1 alpha-2). Empty = allow all"
  type = list(string)
  default = []
}

variable "custom_domain_name" {
  description = "Custom domain name for API Gateway"
  type = string
  default = ""
}

variable "error_threshold" {
  description = "Threshold for API Gateway 5XX error alarm"
  type = number
  default = 10
}

variable "latency_threshold" {
  description = "Threshold for API Gateway latency alarm"
  type = number
  default = 5000
}
