# Local mode detection
locals {
  is_local = var.environment == "local"
  # Use Elasticsearch for local
  opensearch_endpoint = local.is_local ? "elasticsearch:9200" : null
}

# Mock resources for local mode
resource "null_resource" "elasticsearch_mock" {
  count = local.is_local ? 1 : 0
  
  triggers = {
    endpoint  = "http://elasticsearch:9200"
    timestamp = timestamp()
  }
  
  provisioner "local-exec" {
    command = "echo 'Using Elasticsearch at http://localhost:9200 instead of OpenSearch'"
  }
}

# OpenSearch Domain (AWS only)
resource "aws_opensearch_domain" "codehealer" {
  count          = local.is_local ? 0 : 1
  domain_name    = "${var.project_name}-vector-db"
  engine_version = var.engine_version

  cluster_config {
    instance_type            = var.instance_type
    instance_count           = var.instance_count
    dedicated_master_enabled = var.dedicated_master_enabled
    dedicated_master_type    = var.dedicated_master_type
    dedicated_master_count   = var.dedicated_master_count
    zone_awareness_enabled   = var.zone_awareness_enabled

    dynamic "zone_awareness_config" {
      for_each = var.zone_awareness_enabled ? [1] : []
      content {
        availability_zone_count = var.availability_zone_count
      }
    }

    warm_enabled = var.warm_enabled
    warm_count   = var.warm_count
    warm_type    = var.warm_type
  }

  ebs_options {
    ebs_enabled = true
    volume_type = var.volume_type
    volume_size = var.volume_size
    iops        = var.volume_type == "gp3" ? var.iops : null
    throughput  = var.volume_type == "gp3" ? var.throughput : null
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = var.kms_key_id
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"

    custom_endpoint_enabled         = var.custom_endpoint_enabled
    custom_endpoint                 = var.custom_endpoint
    custom_endpoint_certificate_arn = var.custom_endpoint_certificate_arn
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = var.internal_user_database_enabled
    master_user_options {
      master_user_arn      = var.master_user_arn
      master_user_name     = var.master_user_name
      master_user_password = var.master_user_password
    }
  }

  vpc_options {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.opensearch[0].id]
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.index_slow_logs[0].arn
    log_type                 = "INDEX_SLOW_LOGS"
    enabled                  = var.enable_slow_logs
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.search_slow_logs[0].arn
    log_type                 = "SEARCH_SLOW_LOGS"
    enabled                  = var.enable_slow_logs
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.es_application_logs[0].arn
    log_type                 = "ES_APPLICATION_LOGS"
    enabled                  = var.enable_application_logs
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.audit_logs[0].arn
    log_type                 = "AUDIT_LOGS"
    enabled                  = var.enable_audit_logs
  }

  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
    "override_main_response_version"         = "false"
    "knn.algo_param.index_thread_qty"        = var.knn_index_thread_qty
    "knn.memory.circuit_breaker.limit"       = var.knn_memory_circuit_breaker_limit
    "knn.memory.circuit_breaker.enabled"     = "true"
  }

  auto_tune_options {
    desired_state       = var.auto_tune_enabled ? "ENABLED" : "DISABLED"
    rollback_on_disable = "NO_ROLLBACK"

    maintenance_schedule {
      start_at = var.auto_tune_maintenance_start
      duration {
        value = var.auto_tune_maintenance_duration
        unit  = "HOURS"
      }
      cron_expression_for_recurrence = var.auto_tune_maintenance_cron
    }
  }

  snapshot_options {
    automated_snapshot_start_hour = var.snapshot_start_hour
  }

  tags = var.tags

  depends_on = [
    aws_cloudwatch_log_resource_policy.opensearch
  ]
}

# Security Group for OpenSearch (AWS only)
resource "aws_security_group" "opensearch" {
  count       = local.is_local ? 0 : 1
  name        = "${var.project_name}-opensearch-sg"
  description = "Security group for OpenSearch domain"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-opensearch-sg"
    }
  )
}

# OpenSearch Domain Policy (AWS only)
resource "aws_opensearch_domain_policy" "main" {
  count       = local.is_local ? 0 : 1
  domain_name = aws_opensearch_domain.codehealer[0].domain_name

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = var.access_policy_principals
        }
        Action   = "es:*"
        Resource = "${aws_opensearch_domain.codehealer[0].arn}/*"
      }
    ]
  })
}

# CloudWatch Log Groups (AWS only)
resource "aws_cloudwatch_log_group" "index_slow_logs" {
  count             = local.is_local ? 0 : 1
  name              = "/aws/opensearch/${var.project_name}/index-slow-logs"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "search_slow_logs" {
  count             = local.is_local ? 0 : 1
  name              = "/aws/opensearch/${var.project_name}/search-slow-logs"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "es_application_logs" {
  count             = local.is_local ? 0 : 1
  name              = "/aws/opensearch/${var.project_name}/application-logs"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "audit_logs" {
  count             = local.is_local ? 0 : 1
  name              = "/aws/opensearch/${var.project_name}/audit-logs"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# CloudWatch Log Resource Policy (AWS only)
resource "aws_cloudwatch_log_resource_policy" "opensearch" {
  count       = local.is_local ? 0 : 1
  policy_name = "${var.project_name}-opensearch-log-policy"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "es.amazonaws.com"
        }
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# CloudWatch Alarms (AWS only)
resource "aws_cloudwatch_metric_alarm" "cluster_status_red" {
  count               = local.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-opensearch-cluster-red"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ClusterStatus.red"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "OpenSearch cluster status is red"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DomainName = aws_opensearch_domain.codehealer[0].domain_name
    ClientId   = var.aws_account_id
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "cluster_status_yellow" {
  count               = local.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-opensearch-cluster-yellow"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 5
  metric_name         = "ClusterStatus.yellow"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "OpenSearch cluster status is yellow for 5 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DomainName = aws_opensearch_domain.codehealer[0].domain_name
    ClientId   = var.aws_account_id
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "free_storage_space" {
  count               = local.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-opensearch-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Minimum"
  threshold           = var.free_storage_threshold_mb
  alarm_description   = "OpenSearch free storage space is low"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DomainName = aws_opensearch_domain.codehealer[0].domain_name
    ClientId   = var.aws_account_id
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  count               = local.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-opensearch-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Average"
  threshold           = var.cpu_threshold_percent
  alarm_description   = "OpenSearch CPU utilization is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DomainName = aws_opensearch_domain.codehealer[0].domain_name
    ClientId   = var.aws_account_id
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "jvm_memory_pressure" {
  count               = local.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-opensearch-jvm-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "JVMMemoryPressure"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Average"
  threshold           = var.jvm_memory_threshold_percent
  alarm_description   = "OpenSearch JVM memory pressure is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DomainName = aws_opensearch_domain.codehealer[0].domain_name
    ClientId   = var.aws_account_id
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "master_cpu_utilization" {
  count               = var.dedicated_master_enabled && !local.is_local ? 1 : 0
  alarm_name          = "${var.project_name}-opensearch-master-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MasterCPUUtilization"
  namespace           = "AWS/ES"
  period              = 300
  statistic           = "Average"
  threshold           = var.master_cpu_threshold_percent
  alarm_description   = "OpenSearch master node CPU utilization is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DomainName = aws_opensearch_domain.codehealer[0].domain_name
    ClientId   = var.aws_account_id
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "knn_circuit_breaker" {
  count               = local.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-opensearch-knn-breaker"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "KNNCircuitBreakerTriggered"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "OpenSearch k-NN circuit breaker triggered"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DomainName = aws_opensearch_domain.codehealer[0].domain_name
    ClientId   = var.aws_account_id
  }

  alarm_actions = var.alarm_actions
}
