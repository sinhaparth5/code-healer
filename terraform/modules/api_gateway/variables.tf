variable "project_name" {
  type = string
}

variable "stage_name" {
  type = string
}

variable "lambda_function_name" {
  type = string
}

variable "lambda_invoke_arn" {
  type = string
}

variable "authorizer_lambda_invoke_arn" {
  type = string
}

variable "authorizer_role_arn" {
  type = string
}

variable "cloudwatch_role_arn" {
  type = string
}

variable "log_retention_days" {
  type = number
  default = 30
}

variable "enable_xray" {
  type = bool
  default = true
}

variable "logging_level" {
  type = string
  default = "INFO"
}

variable "enable_data_trace" {
  type = bool
  default = false
}

variable "throttle_burst_limit" {
  type = number
  default = 5000
}

variable "throttle_rate_limit" {
  type = number
  default = 10000
}