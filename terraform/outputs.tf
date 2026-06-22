output "app_url" {
  description = "HTTP URL for the deployed application."
  value       = "http://${aws_lb.app.dns_name}"
}

output "ecr_repository_name" {
  description = "ECR repository name for application images."
  value       = aws_ecr_repository.app.name
}

output "ecr_repository_url" {
  description = "ECR repository URL for application images."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.app.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.app.name
}
