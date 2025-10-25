output "incidents_table_name" {
  value = aws_dynamodb_table.incidents.name
}

output "incidents_table_arn" {
  value = aws_dynamodb_table.incidents.arn
}

output "incidents_table_id" {
  value = aws_dynamodb_table.incidents.id
}

output "incidents_stream_arn" {
  value = var.enable_streams ? aws_dynamodb_table.incidents.stream_arn : null
}

output "resolutions_table_name" {
  value = aws_dynamodb_table.resolutions.name
}

output "resolutions_table_arn" {
  value = aws_dynamodb_table.resolutions.arn
}

output "resolutions_table_id" {
  value = aws_dynamodb_table.resolutions.id
}

output "resolutions_stream_arn" {
  value = var.enable_streams ? aws_dynamodb_table.resolutions.stream_arn : null
}

output "metrics_table_name" {
  value = aws_dynamodb_table.metrics.name
}

output "metrics_table_arn" {
  value = aws_dynamodb_table.metrics.arn
}

output "metrics_table_id" {
  value = aws_dynamodb_table.metrics.id
}