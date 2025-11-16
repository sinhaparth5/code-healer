resource "null_resource" "install_dependencies" {
  triggers = {
    requirements = filemd5("${path.root}/../requirements.txt")
  }

  provisioner "local-exec" {
    command = "pip install -r ${path.root}/../requirements.txt -t ${path.root}/../src --upgrade"
    working_dir = path.root
  }
}

data "archive_file" "lambda_package" {
  type = "zip"
  source_dir = "${path.root}/../src"
  output_path = "${path.root}/../deployment/lambda_package.zip"

  depends_on = [ null_resource.install_dependencies ]
}

resource "aws_lambda_function" "codehealer" {
    filename = data.archive_file.lambda_package.output_path
    function_name = "${var.project_name}-handler"
    role = aws_iam_role.lambda_execution.arn
    handler = "lambda_handler.handler"
    source_code_hash = data.archive_file.lambda_package.output_base64sha256
    runtime = var.runtime
    timeout = var.timeout
    memory_size = var.memory_size
    
    environment {
      variables = merge(
        {
          ENVIRONMENT = var.environment
          LOG_LEVEL = var.log_level
          AWS_REGION = var.aws_region
          
          # AWS Services
          OPENSEARCH_ENDPOINT = var.opensearch_endpoint
          DYNAMODB_TABLE_NAME = var.dynamodb_table_name
          
          # SageMaker Endpoints
          SAGEMAKER_LLAMA_ENDPOINT = var.sagemaker_llm_endpoint
          SAGEMAKER_EMBEDDING_ENDPOINT = var.sagemaker_embedding_endpoint
          
          # Secret ARNs (Lambda will fetch these at runtime)
          GITHUB_TOKEN_SECRET_ARN = var.github_token_secret_arn
          GITHUB_WEBHOOK_SECRET = var.github_webhook_secret_name
          SLACK_TOKEN_SECRET_ARN = var.slack_token_secret_arn
          ARGOCD_TOKEN_SECRET_ARN = var.argocd_token_secret_arn
          K8S_CONFIG_SECRET_ARN = var.k8s_config_secret_arn
          OPENAI_API_KEY_SECRET_ARN = var.openai_api_key_secret_arn
          NVIDIA_NIM_API_KEY_SECRET_ARN = var.nvidia_nim_api_key_secret_arn
          APP_CONFIG_SECRET_ARN = var.app_config_secret_arn
          
          # Application Configuration
          CONFIDENCE_THRESHOLD = var.confidence_threshold
          AUTO_FIX_ENABLED = var.auto_fix_enabled
          MAX_RETRY_ATTEMPTS = var.max_retry_attempts
          
          # Feature Flags
          ENABLE_AUTO_FIX = var.enable_auto_fix
          ENABLE_SLACK_NOTIFICATIONS = var.enable_slack_notifications
          ENABLE_LLM_ANALYSIS = var.enable_llm_analysis
        },
        var.additional_env_vars
      )
    }

    vpc_config {
      subnet_ids = var.subnet_ids
      security_group_ids = var.security_group_ids
    }

    tracing_config {
      mode = var.enable_xray ? "Active" : "PassThrough"
    }

    dead_letter_config {
      target_arn = aws_sqs_queue.dlq.arn
    }

    reserved_concurrent_executions = var.reserved_concurrent_executions

    depends_on = [ aws_cloudwatch_log_group.lambda ]
}

resource "aws_lambda_function" "authorizer" {
  filename = data.archive_file.lambda_package.output_path
  function_name = "${var.project_name}-authorizer"
  role = aws_iam_role.lambda_execution.arn
  handler = "lambda_handler.authorizer"
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  runtime = var.runtime
  timeout = 10
  memory_size = 256

  environment {
    variables = {
      GITHUB_WEBHOOK_SECRET_ARN = var.github_webhook_secret_arn
      AWS_REGION = var.aws_region
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }
  
  depends_on = [aws_cloudwatch_log_group.authorizer]
}

resource "aws_cloudwatch_log_group" "lambda" {
  name = "/aws/lambda/${var.project_name}-handler"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "authorizer" {
  name = "/aws/lambda/${var.project_name}-authorizer"
  retention_in_days = var.log_retention_days
}

resource "aws_sqs_queue" "dlq" {
  name = "${var.project_name}-dlq"
  message_retention_seconds = 1209600
  visibility_timeout_seconds = var.timeout * 6
  tags = var.tags
}

resource "aws_lambda_event_source_mapping" "dlq_trigger" {
  event_source_arn = aws_sqs_queue.dlq.arn
  function_name = aws_lambda_function.codehealer.arn
  enabled = false
}

resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
            Service = "lambda.amazonaws.com"
        }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count = length(var.subnet_ids) > 0 ? 1 : 0
  role = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_xray" {
    count = var.enable_xray ? 1 : 0
    role = aws_iam_role.lambda_execution.name
    policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "${var.project_name}-lambda-permissions"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Resource = [
            var.github_token_secret_arn,
            var.github_webhook_secret_arn,
            var.slack_token_secret_arn,
            var.argocd_token_secret_arn,
            var.k8s_config_secret_arn,
            var.openai_api_key_secret_arn,
            var.nvidia_nim_api_key_secret_arn,
            var.app_config_secret_arn
          ]
        },
        {
          Effect = "Allow"
          Action = [
            "dynamodb:PutItem",
            "dynamodb:GetItem",
            "dynamodb:UpdateItem",
            "dynamodb:Query",
            "dynamodb:Scan"
          ]
          Resource = [
            var.dynamodb_table_arn,
            "${var.dynamodb_table_arn}/index/*"
          ]
        },
        {
          Effect = "Allow"
          Action = [
            "es:ESHttpPost",
            "es:ESHttpPut",
            "es:ESHttpGet"
          ]
          Resource = "${var.opensearch_domain_arn}/*"
        },
        {
          Effect = "Allow"
          Action = [
            "sagemaker:InvokeEndpoint"
          ]
          Resource = [
            var.sagemaker_llm_endpoint_arn,
            var.sagemaker_embedding_endpoint_arn
          ]
        },
        {
          Effect = "Allow"
          Action = [
            "sqs:SendMessage"
          ]
          Resource = aws_sqs_queue.dlq.arn
        },
        {
          Effect = "Allow"
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ]
          Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/${var.project_name}-*:*"
        }
      ],
      # Only add KMS statement if KMS key exists
      var.kms_key_arn != null ? [
        {
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = [var.kms_key_arn]
          Condition = {
            StringEquals = {
              "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
            }
          }
        }
      ] : []
    )
  })
}
resource "aws_lambda_alias" "live" {
  name = "live"
  function_name = aws_lambda_function.codehealer.function_name
  function_version = aws_lambda_function.codehealer.version
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = 2
  metric_name = "Errors"
  namespace = "AWS/Lambda"
  period = 300
  statistic = "Sum"
  threshold = 10
  alarm_description = "Lambda function error rate exceeded"
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.codehealer.function_name
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name = "${var.project_name}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = 2
  metric_name = "Duration"
  namespace = "AWS/Lambda"
  period = 300
  statistic = "Average"
  alarm_description = "Lambda function duration approaching timeout"
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.codehealer.function_name
  }

  alarm_actions = var.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name = "${var.project_name}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = 1
  metric_name = "Throttles"
  namespace = "AWS/Lambda"
  period = 300
  statistic = "Sum"
  threshold = 5
  alarm_description = "Lambda function being throttled"
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.codehealer.function_name
  }

  alarm_actions = var.alarm_actions
}
