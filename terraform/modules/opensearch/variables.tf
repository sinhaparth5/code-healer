variable "project_name" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "engine_version" {
  type    = string
  default = "OpenSearch_2.11"
}

variable "instance_type" {
  type    = string
  default = "r6g.large.search"
}

variable "instance_count" {
  type    = number
  default = 2
}

variable "dedicated_master_enabled" {
  type    = bool
  default = true
}

variable "dedicated_master_type" {
  type    = string
  default = "r6g.large.search"
}

variable "dedicated_master_count" {
  type    = number
  default = 3
}

variable "zone_awareness_enabled" {
  type    = bool
  default = true
}

variable "availability_zone_count" {
  type    = number
  default = 2
}

variable "warm_enabled" {
  type    = bool
  default = false
}

variable "warm_count" {
  type    = number
  default = 0
}

variable "warm_type" {
  type    = string
  default = "ultrawarm1.medium.search"
}

variable "volume_type" {
  type    = string
  default = "gp3"
}

variable "volume_size" {
  type    = number
  default = 100
}

variable "iops" {
  type    = number
  default = 3000
}

variable "throughput" {
  type    = number
  default = 125
}

variable "kms_key_id" {
  type    = string
  default = null
}

variable "custom_endpoint_enabled" {
  type    = bool
  default = false
}

variable "custom_endpoint" {
  type    = string
  default = null
}

variable "custom_endpoint_certificate_arn" {
  type    = string
  default = null
}

variable "internal_user_database_enabled" {
  type    = bool
  default = false
}

variable "master_user_arn" {
  type    = string
  default = null
}

variable "master_user_name" {
  type    = string
  default = null
}

variable "master_user_password" {
  type      = string
  default   = null
  sensitive = true
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "allowed_cidr_blocks" {
  type = list(string)
}

variable "access_policy_principals" {
  type = list(string)
}

variable "enable_slow_logs" {
  type    = bool
  default = true
}

variable "enable_application_logs" {
  type    = bool
  default = true
}

variable "enable_audit_logs" {
  type    = bool
  default = true
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "knn_index_thread_qty" {
  type    = string
  default = "1"
}

variable "knn_memory_circuit_breaker_limit" {
  type    = string
  default = "50"
}

variable "auto_tune_enabled" {
  type    = bool
  default = true
}

variable "auto_tune_maintenance_start" {
  type    = string
  default = "2024-01-01T00:00:00Z"
}

variable "auto_tune_maintenance_duration" {
  type    = number
  default = 2
}

variable "auto_tune_maintenance_cron" {
  type    = string
  default = "cron(0 3 ? * SUN *)"
}

variable "snapshot_start_hour" {
  type    = number
  default = 3
}

variable "free_storage_threshold_mb" {
  type    = number
  default = 10240
}

variable "cpu_threshold_percent" {
  type    = number
  default = 80
}

variable "jvm_memory_threshold_percent" {
  type    = number
  default = 85
}

variable "master_cpu_threshold_percent" {
  type    = number
  default = 50
}

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}