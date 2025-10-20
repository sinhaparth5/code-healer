resource "aws_api_gateway_rest_api" "codehealer_webhook" {
  name = "${var.project_name}-webhook-api"
  description = "API Gateway for receiving GitHub webhook events"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-webhook-api"
      Component = "api-gateway"
      ManagedBy = "terraform"
    }
  )
}


