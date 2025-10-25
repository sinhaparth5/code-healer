variable "project_name" {
  type = string
}

variable "billing_mode" {
  type    = string
  default = "PAY_PER_REQUEST"
}

variable "read_capacity" {
  type    = number
  default = 5
}

variable "write_capacity" {
  type    = number
  default = 5
}

variable "gsi_read_capacity" {
  type    = number
  default = 5
}

variable "gsi_write_capacity" {
  type    = number
  default = 5
}

variable "enable_ttl" {
  type    = bool
  default = true
}

variable "enable_point_in_time_recovery" {
  type    = bool
  default = true
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "enable_streams" {
  type    = bool
  default = false
}

variable "stream_view_type" {
  type    = string
  default = "NEW_AND_OLD_IMAGES"
}

variable "enable_autoscaling" {
  type    = bool
  default = true
}

variable "autoscaling_read_max_capacity" {
  type    = number
  default = 100
}

variable "autoscaling_write_max_capacity" {
  type    = number
  default = 100
}

variable "autoscaling_read_target_utilization" {
  type    = number
  default = 70
}

variable "autoscaling_write_target_utilization" {
  type    = number
  default = 70
}

variable "scale_in_cooldown" {
  type    = number
  default = 300
}

variable "scale_out_cooldown" {
  type    = number
  default = 60
}

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}