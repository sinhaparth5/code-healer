variable "project_name" {
  type = string
}

variable "llm_container_image" {
  type = string
}

variable "llm_model_data_url" {
  type = string
  default = null
}

variable "llm_environment_vars" {
  type = map(string)
  default = {}
}

variable "llm_instance_count" {
  type = number
  default = 1
}

variable "llm_instance_type" {
  type = string
  default = "ml.g5.xlarge"
}

variable "llm_serverless_max_concurrency" {
  type = number
  default = 20
}

variable "llm_serverless_memory_size" {
  type = number
  default = 6144
}

variable "embedding_container_image" {
  type = string
}

variable "embedding_model_data_url" {
  type = string
  default = null
}

variable "embedding_environment_vars" {
  type = map(string)
  default = {}
}

variable "embedding_instance_count" {
  type = number
  default = 1
}

variable "embedding_instance_type" {
  type = string
  default = "ml.g5.xlarge"
}

variable "embedding_serverless_max_concurrency" {
  type = number
  default = 50
}

variable "embedding_serverless_memory_size" {
  type = number
  default = 4096
}

variable "model_artifacts_bucket_arn" {
  type = string
}

variable "data_capture_bucket_arn" {
  type = string
}

variable "data_capture_s3_uri" {
  type = string
}

variable "async_output_s3_uri" {
  type = string
}

variable "enable_data_capture" {
  type = bool
  default = true
}

variable "data_capture_sampling_percentage" {
  type = number
  default = 10
}

variable "max_concurrent_invocations" {
  type = number
  default = 20
}

variable "log_retention_days" {
  type = number
  default = 30
}

variable "llm_latency_threshold_ms" {
  type = number
  default = 30000
}

variable "embedding_latency_threshold_ms" {
  type = number
  default = 5000
}

variable "alarm_actions" {
  type = list(string)
  default = [ ]
}

variable "enable_autoscaling" {
  type = bool
  default = true
}

variable "llm_min_capacity" {
  type = number
  default = 1
}

variable "llm_max_capacity" {
  type = number
  default = 5
}

variable "llm_target_invocations_per_instance" {
  type = number
  default = 100
}

variable "embedding_min_capacity" {
  type = number
  default = 1
}

variable "embedding_max_capacity" {
  type = number
  default = 5
}

variable "embedding_target_invocations_per_instance" {
    type = number
    default = 200
}

variable "tags" {
  type = map(string)
  default = {}
}