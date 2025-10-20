variable "project_name" {
  description = "Name of the project"
  type = string
  default = "codehealer"
}

variable "stage_name" {
  description = "API Gateway stage name"
  type = string
  default = "prod"
  validation {
    condition = contains(["dev", "staging", "prod"], var.stage_name)
    error_message = "Stage name must be one of: dev, staging, prod"
  }
}

variable "lambda_invoke_arn" {
  description = "ARN of the lambda function to invoke"
  type = string
}

variable "lamdba_function_name" {
  description = "Name of the Lambda function"
  type = string
}

variable "log_retention_days" {
  description = "Number of days to retain API Gateway logs"
  type = number
  default = 7
  validation {
    condition = contains([1, 2, 5, 7, 14, 30, 60, 90, 120, 150, 180, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch Logs retention period"
  }
}

variable "api_logging_level" {
  description = "Logging level for API Gateway (OFF, ERROR, INFO)"
  type = string
  default = "INFO"
  validation {
    condition = contains(["OFF", "ERROR", "INFO"], var.api_logging_level)
    error_message = "Logging level must be one of: OFF, ERROR, INFO"
  }
}

variable "enable_data_trace" {
  description = "Enable detailed Cloudwatch logging for API Gateway"
  type = bool
  default = false
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray tracing"
  type = bool
  default = true
}

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
  description = "WAF rate limit (requests per 5 minutes for a single IP)"
  type = number
  default = 2000
}

variable "allowed_countries" {
  description = "List of allowed country codes (ISO 3166-1 alpha-2). Empty list = allow all"
  type = list(string)
  default = []
  # Example ["US", "GB"]
}

variable "custom_domain_name" {
  description = "Custom domain name for API Gateway (leave empty to skip)"
  type = string
  default = ""
}

variable "certificate_arn" {
  description = "ARN of ACM certificate for custom domain"
  type = string
  default = ""
}

variable "error_threshold" {
  description = "Threshold for 5XX error alarm"
  type = number
  default = 10
}

variable "latency_threshold" {
  description = "Threshold for latency alarm (milliseconds)"
  type = number
  default = 5000
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms"
  type = string
  default = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type = map(string)
  default = {
    Project = "CodeHealer"
    Environment = "Production"
    Terraform = "true"
  }
}
