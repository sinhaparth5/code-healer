output "domain_id" {
  value       = var.environment == "local" ? "mock-opensearch-domain" : aws_opensearch_domain.codehealer[0].domain_id
  description = "OpenSearch domain ID or mock ID"
}

output "domain_name" {
  value       = var.environment == "local" ? "elasticsearch" : aws_opensearch_domain.codehealer[0].domain_name
  description = "OpenSearch domain name or Elasticsearch name"
}

output "domain_arn" {
  value       = var.environment == "local" ? "arn:aws:es:us-east-1:000000000000:domain/mock-opensearch" : aws_opensearch_domain.codehealer[0].arn
  description = "OpenSearch domain ARN or mock ARN"
}

output "endpoint" {
  value       = var.environment == "local" ? "http://elasticsearch:9200" : aws_opensearch_domain.codehealer[0].endpoint
  description = "OpenSearch endpoint URL or Elasticsearch URL"
}

output "dashboard_endpoint" {
  value       = var.environment == "local" ? "http://localhost:9200" : aws_opensearch_domain.codehealer[0].dashboard_endpoint
  description = "OpenSearch dashboard endpoint or Elasticsearch URL"
}

output "security_group_id" {
  value       = var.environment == "local" ? "sg-mock-opensearch" : aws_security_group.opensearch[0].id
  description = "Security group ID for OpenSearch or mock SG"
}

output "kibana_endpoint" {
  value       = var.environment == "local" ? "http://localhost:9200/_dashboards" : "https://${aws_opensearch_domain.codehealer[0].endpoint}/_dashboards"
  description = "Kibana/OpenSearch Dashboards endpoint"
}

output "vpc_id" {
  value       = var.vpc_id
  description = "VPC ID where OpenSearch is deployed"
}

output "subnet_ids" {
  value       = var.subnet_ids
  description = "Subnet IDs where OpenSearch is deployed"
}
