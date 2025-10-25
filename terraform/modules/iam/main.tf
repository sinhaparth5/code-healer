resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${var.project_name}-apigateway-cloudwatch"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "apigateway.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

resource "aws_iam_role" "lambda_authorizer" {
  name = "${var.project_name}-lambda-authorizer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "apigateway.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "lambda_authorizer" {
  name = "${var.project_name}-authorizer-invoke"
  role = aws_iam_role.lambda_authorizer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "lambda:InvokeFunction"
      ]
      Resource = var.authorizer_lambda_arn
    }]
  })
}

resource "aws_iam_role" "github_actions" {
  count = var.enable_github_oidc ? 1 : 0
  name  = "${var.project_name}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = var.github_oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "github_actions" {
  count = var.enable_github_oidc ? 1 : 0
  name  = "${var.project_name}-github-actions-deploy"
  role  = aws_iam_role.github_actions[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:PublishVersion",
          "lambda:UpdateAlias",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration"
        ]
        Resource = [
          var.lambda_function_arn,
          var.authorizer_lambda_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${var.deployment_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_policy" "opensearch_access" {
  name        = "${var.project_name}-opensearch-access"
  description = "Policy for accessing OpenSearch domain"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPut",
          "es:ESHttpPost",
          "es:ESHttpDelete",
          "es:ESHttpHead"
        ]
        Resource = [
          var.opensearch_domain_arn,
          "${var.opensearch_domain_arn}/*"
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "dynamodb_access" {
  name        = "${var.project_name}-dynamodb-access"
  description = "Policy for accessing DynamoDB tables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable"
        ]
        Resource = [
          var.incidents_table_arn,
          "${var.incidents_table_arn}/index/*",
          var.resolutions_table_arn,
          "${var.resolutions_table_arn}/index/*",
          var.metrics_table_arn,
          "${var.metrics_table_arn}/index/*"
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "sagemaker_invoke" {
  name        = "${var.project_name}-sagemaker-invoke"
  description = "Policy for invoking SageMaker endpoints"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint",
          "sagemaker:InvokeEndpointAsync"
        ]
        Resource = [
          var.sagemaker_llm_endpoint_arn,
          var.sagemaker_embedding_endpoint_arn
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "secrets_access" {
  name        = "${var.project_name}-secrets-access"
  description = "Policy for accessing Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.project_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = var.secrets_kms_key_arn != null ? [var.secrets_kms_key_arn] : []
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "kubernetes_access" {
  name        = "${var.project_name}-kubernetes-access"
  description = "Policy for accessing Kubernetes API"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster",
          "eks:ListClusters"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "github_api_access" {
  name        = "${var.project_name}-github-api-access"
  description = "Policy for GitHub API operations"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.project_name}/github-*"
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "slack_api_access" {
  name        = "${var.project_name}-slack-api-access"
  description = "Policy for Slack API operations"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.project_name}/slack-*"
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "argocd_api_access" {
  name        = "${var.project_name}-argocd-api-access"
  description = "Policy for ArgoCD API operations"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.project_name}/argocd-*"
        ]
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role" "monitoring" {
  name = "${var.project_name}-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = [
          "cloudwatch.amazonaws.com",
          "events.amazonaws.com"
        ]
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "monitoring" {
  name = "${var.project_name}-monitoring-access"
  role = aws_iam_role.monitoring.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/${var.project_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_topic_arns
      }
    ]
  })
}

resource "aws_iam_user" "ci_deployer" {
  count = var.create_ci_user ? 1 : 0
  name  = "${var.project_name}-ci-deployer"
  path  = "/system/"

  tags = var.tags
}

resource "aws_iam_user_policy_attachment" "ci_deployer_lambda" {
  count      = var.create_ci_user ? 1 : 0
  user       = aws_iam_user.ci_deployer[0].name
  policy_arn = aws_iam_policy.github_api_access.arn
}

resource "aws_iam_access_key" "ci_deployer" {
  count = var.create_ci_user ? 1 : 0
  user  = aws_iam_user.ci_deployer[0].name
}

resource "aws_iam_policy" "xray_access" {
  count       = var.enable_xray ? 1 : 0
  name        = "${var.project_name}-xray-access"
  description = "Policy for X-Ray tracing"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "vpc_access" {
  count       = var.enable_vpc ? 1 : 0
  name        = "${var.project_name}-vpc-access"
  description = "Policy for VPC access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}