resource "aws_sagemaker_model" "llm" {
  name               = "${var.project_name}-llm-model"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    image          = var.llm_container_image
    model_data_url = var.llm_model_data_url
    environment    = var.llm_environment_vars
  }

  tags = var.tags
}

resource "aws_sagemaker_model" "embedding" {
  name               = "${var.project_name}-embedding-model"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    image          = var.embedding_container_image
    model_data_url = var.embedding_model_data_url
    environment    = var.embedding_environment_vars
  }

  tags = var.tags
}

resource "aws_sagemaker_endpoint_configuration" "llm" {
  name = "${var.project_name}-llm-config"

  production_variants {
    variant_name           = "AllTraffic"
    model_name            = aws_sagemaker_model.llm.name
    initial_instance_count = var.llm_instance_count
    instance_type         = var.llm_instance_type
    initial_variant_weight = 1

    serverless_config {
      max_concurrency   = var.llm_serverless_max_concurrency
      memory_size_in_mb = var.llm_serverless_memory_size
    }
  }

  data_capture_config {
    enable_capture              = var.enable_data_capture
    initial_sampling_percentage = var.data_capture_sampling_percentage
    destination_s3_uri          = "${var.data_capture_s3_uri}/llm"

    capture_options {
      capture_mode = "InputAndOutput"
    }
  }

  async_inference_config {
    output_config {
      s3_output_path = "${var.async_output_s3_uri}/llm"
    }

    client_config {
      max_concurrent_invocations_per_instance = var.max_concurrent_invocations
    }
  }

  tags = var.tags
}

resource "aws_sagemaker_endpoint_configuration" "embedding" {
  name = "${var.project_name}-embedding-config"

  production_variants {
    variant_name           = "AllTraffic"
    model_name            = aws_sagemaker_model.embedding.name
    initial_instance_count = var.embedding_instance_count
    instance_type         = var.embedding_instance_type
    initial_variant_weight = 1

    serverless_config {
      max_concurrency   = var.embedding_serverless_max_concurrency
      memory_size_in_mb = var.embedding_serverless_memory_size
    }
  }

  data_capture_config {
    enable_capture              = var.enable_data_capture
    initial_sampling_percentage = var.data_capture_sampling_percentage
    destination_s3_uri          = "${var.data_capture_s3_uri}/embedding"

    capture_options {
      capture_mode = "InputAndOutput"
    }
  }

  tags = var.tags
}

resource "aws_sagemaker_endpoint" "llm" {
  name                 = "${var.project_name}-llm-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.llm.name

  tags = var.tags
}

resource "aws_sagemaker_endpoint" "embedding" {
  name                 = "${var.project_name}-embedding-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.embedding.name

  tags = var.tags
}

resource "aws_iam_role" "sagemaker_execution" {
  name = "${var.project_name}-sagemaker-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "sagemaker.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "sagemaker_permissions" {
  name = "${var.project_name}-sagemaker-permissions"
  role = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${var.model_artifacts_bucket_arn}/*",
          var.model_artifacts_bucket_arn,
          "${var.data_capture_bucket_arn}/*",
          var.data_capture_bucket_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:CreateLogGroup"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "llm_endpoint" {
  name              = "/aws/sagemaker/Endpoints/${aws_sagemaker_endpoint.llm.name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "embedding_endpoint" {
  name              = "/aws/sagemaker/Endpoints/${aws_sagemaker_endpoint.embedding.name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "llm_invocation_errors" {
  alarm_name          = "${var.project_name}-llm-invocation-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelInvocationErrors"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "LLM endpoint invocation errors exceeded threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.llm.name
    VariantName  = "AllTraffic"
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "llm_latency" {
  alarm_name          = "${var.project_name}-llm-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Average"
  threshold           = var.llm_latency_threshold_ms
  alarm_description   = "LLM endpoint latency exceeded threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.llm.name
    VariantName  = "AllTraffic"
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "embedding_invocation_errors" {
  alarm_name          = "${var.project_name}-embedding-invocation-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelInvocationErrors"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Embedding endpoint invocation errors exceeded threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.embedding.name
    VariantName  = "AllTraffic"
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "embedding_latency" {
  alarm_name          = "${var.project_name}-embedding-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Average"
  threshold           = var.embedding_latency_threshold_ms
  alarm_description   = "Embedding endpoint latency exceeded threshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.embedding.name
    VariantName  = "AllTraffic"
  }

  alarm_actions = var.alarm_actions
}

resource "aws_appautoscaling_target" "llm" {
  count              = var.enable_autoscaling ? 1 : 0
  max_capacity       = var.llm_max_capacity
  min_capacity       = var.llm_min_capacity
  resource_id        = "endpoint/${aws_sagemaker_endpoint.llm.name}/variant/AllTraffic"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  service_namespace  = "sagemaker"
}

resource "aws_appautoscaling_policy" "llm" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${var.project_name}-llm-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.llm[0].resource_id
  scalable_dimension = aws_appautoscaling_target.llm[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.llm[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.llm_target_invocations_per_instance

    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_target" "embedding" {
  count              = var.enable_autoscaling ? 1 : 0
  max_capacity       = var.embedding_max_capacity
  min_capacity       = var.embedding_min_capacity
  resource_id        = "endpoint/${aws_sagemaker_endpoint.embedding.name}/variant/AllTraffic"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  service_namespace  = "sagemaker"
}

resource "aws_appautoscaling_policy" "embedding" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${var.project_name}-embedding-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.embedding[0].resource_id
  scalable_dimension = aws_appautoscaling_target.embedding[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.embedding[0].service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.embedding_target_invocations_per_instance

    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}