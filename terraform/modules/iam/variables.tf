variable "project_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "authorizer_lambda_arn" {
  type = string
  default = ""
}

variable "lambda_function_arn" {
  type = string
  default = ""
}

variable "opensearch_domain_arn" {
  type = string
}

variable "incidents_table_arn" {
  type = string
}

variable "resolutions_table_arn" {
  type = string
}

variable "metrics_table_arn" {
  type = string
}

variable "sagemaker_llm_endpoint_arn" {
  type = string
}

variable "sagemaker_embedding_endpoint_arn" {
  type = string
}

variable "secrets_kms_key_arn" {
  type    = string
  default = null
}

variable "sns_topic_arns" {
  type    = list(string)
  default = []
}

variable "enable_github_oidc" {
  type    = bool
  default = false
}

variable "github_oidc_provider_arn" {
  type    = string
  default = ""
}

variable "github_repo" {
  type    = string
  default = ""
}

variable "deployment_bucket_arn" {
  type    = string
  default = ""
}

variable "create_ci_user" {
  type    = bool
  default = false
}

variable "enable_xray" {
  type    = bool
  default = true
}

variable "enable_vpc" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}