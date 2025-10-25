resource "aws_dynamodb_table" "incidents" {
  name           = "${var.project_name}-incidents"
  billing_mode   = var.billing_mode
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null
  hash_key       = "incident_id"
  range_key      = "timestamp"

  attribute {
    name = "incident_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "failure_type"
    type = "S"
  }

  attribute {
    name = "environment"
    type = "S"
  }

  attribute {
    name = "service_name"
    type = "S"
  }

  attribute {
    name = "resolution_status"
    type = "S"
  }

  global_secondary_index {
    name            = "FailureTypeIndex"
    hash_key        = "failure_type"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  global_secondary_index {
    name            = "EnvironmentIndex"
    hash_key        = "environment"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  global_secondary_index {
    name            = "ServiceIndex"
    hash_key        = "service_name"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  global_secondary_index {
    name            = "ResolutionStatusIndex"
    hash_key        = "resolution_status"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  ttl {
    attribute_name = "ttl"
    enabled        = var.enable_ttl
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  stream_enabled   = var.enable_streams
  stream_view_type = var.enable_streams ? var.stream_view_type : null

  lifecycle {
    ignore_changes = [read_capacity, write_capacity]
  }

  tags = var.tags
}

resource "aws_dynamodb_table" "resolutions" {
  name           = "${var.project_name}-resolutions"
  billing_mode   = var.billing_mode
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null
  hash_key       = "resolution_id"
  range_key      = "incident_id"

  attribute {
    name = "resolution_id"
    type = "S"
  }

  attribute {
    name = "incident_id"
    type = "S"
  }

  attribute {
    name = "applied_timestamp"
    type = "N"
  }

  attribute {
    name = "outcome"
    type = "S"
  }

  global_secondary_index {
    name            = "IncidentIndex"
    hash_key        = "incident_id"
    range_key       = "applied_timestamp"
    projection_type = "ALL"
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  global_secondary_index {
    name            = "OutcomeIndex"
    hash_key        = "outcome"
    range_key       = "applied_timestamp"
    projection_type = "ALL"
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  ttl {
    attribute_name = "ttl"
    enabled        = var.enable_ttl
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  stream_enabled   = var.enable_streams
  stream_view_type = var.enable_streams ? var.stream_view_type : null

  lifecycle {
    ignore_changes = [read_capacity, write_capacity]
  }

  tags = var.tags
}

resource "aws_dynamodb_table" "metrics" {
  name           = "${var.project_name}-metrics"
  billing_mode   = var.billing_mode
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null
  hash_key       = "metric_name"
  range_key      = "timestamp"

  attribute {
    name = "metric_name"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "environment"
    type = "S"
  }

  global_secondary_index {
    name            = "EnvironmentMetricIndex"
    hash_key        = "environment"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = var.billing_mode == "PROVISIONED" ? var.gsi_read_capacity : null
    write_capacity  = var.billing_mode == "PROVISIONED" ? var.gsi_write_capacity : null
  }

  ttl {
    attribute_name = "ttl"
    enabled        = var.enable_ttl
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  lifecycle {
    ignore_changes = [read_capacity, write_capacity]
  }

  tags = var.tags
}

resource "aws_appautoscaling_target" "incidents_read" {
  count              = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0
  max_capacity       = var.autoscaling_read_max_capacity
  min_capacity       = var.read_capacity
  resource_id        = "table/${aws_dynamodb_table.incidents.name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "incidents_read" {
  count              = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0
  name               = "${var.project_name}-incidents-read-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.incidents_read[0].resource_id
  scalable_dimension = aws_appautoscaling_target.incidents_read[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.incidents_read[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.autoscaling_read_target_utilization

    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }

    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

resource "aws_appautoscaling_target" "incidents_write" {
  count              = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0
  max_capacity       = var.autoscaling_write_max_capacity
  min_capacity       = var.write_capacity
  resource_id        = "table/${aws_dynamodb_table.incidents.name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "incidents_write" {
  count              = var.billing_mode == "PROVISIONED" && var.enable_autoscaling ? 1 : 0
  name               = "${var.project_name}-incidents-write-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.incidents_write[0].resource_id
  scalable_dimension = aws_appautoscaling_target.incidents_write[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.incidents_write[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.autoscaling_write_target_utilization

    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }

    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

resource "aws_cloudwatch_metric_alarm" "incidents_read_throttle" {
  alarm_name          = "${var.project_name}-incidents-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "DynamoDB incidents table read throttle events exceeded"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.incidents.name
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "incidents_write_throttle" {
  alarm_name          = "${var.project_name}-incidents-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "DynamoDB incidents table write throttle events exceeded"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.incidents.name
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "incidents_system_errors" {
  alarm_name          = "${var.project_name}-incidents-system-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "SystemErrors"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "DynamoDB incidents table system errors exceeded"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.incidents.name
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "resolutions_read_throttle" {
  alarm_name          = "${var.project_name}-resolutions-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "DynamoDB resolutions table read throttle events exceeded"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.resolutions.name
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "resolutions_write_throttle" {
  alarm_name          = "${var.project_name}-resolutions-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "DynamoDB resolutions table write throttle events exceeded"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.resolutions.name
  }

  alarm_actions = var.alarm_actions
}