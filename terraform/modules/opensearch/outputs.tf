output "domain_id" {
  value = aws_opensearch_domain.codehealer.domain_id
}

output "domain_name" {
  value = aws_opensearch_domain.codehealer.domain_name
}

output "domain_arn" {
  value = aws_opensearch_domain.codehealer.arn
}

output "endpoint" {
  value = aws_opensearch_domain.codehealer.endpoint
}

output "dashboard_endpoint" {
  value = aws_opensearch_domain.codehealer.dashboard_endpoint
}

output "security_group_id" {
  value = aws_security_group.opensearch.id
}

output "kibana_endpoint" {
  value = "https://${aws_opensearch_domain.codehealer.endpoint}/_dashboards"
}

output "vpc_id" {
  value = var.vpc_id
}

output "subnet_ids" {
  value = var.subnet_ids
}