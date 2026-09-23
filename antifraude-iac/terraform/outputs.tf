# ==============================================================================
# Terraform Outputs - Información de Despliegue
# ==============================================================================

# ------------------------------------------------------------------------------
# Networking
# ------------------------------------------------------------------------------
output "vpc_id" {
  description = "ID de la VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "IDs de las subnets privadas"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs de las subnets públicas"
  value       = aws_subnet.public[*].id
}

# ------------------------------------------------------------------------------
# Load Balancer
# ------------------------------------------------------------------------------
output "alb_dns_name" {
  description = "DNS name del Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID del ALB (para Route53)"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "ARN del Application Load Balancer"
  value       = aws_lb.main.arn
}

output "application_url" {
  description = "URL de la aplicación"
  value       = var.certificate_arn != "" ? "https://${var.domain_name != "" ? var.domain_name : aws_lb.main.dns_name}" : "http://${aws_lb.main.dns_name}"
}

# ------------------------------------------------------------------------------
# ECS
# ------------------------------------------------------------------------------
output "ecs_cluster_name" {
  description = "Nombre del ECS Cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN del ECS Cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "Nombre del ECS Service"
  value       = aws_ecs_service.app.name
}

output "ecs_task_definition_arn" {
  description = "ARN de la Task Definition"
  value       = aws_ecs_task_definition.app.arn
}

# ------------------------------------------------------------------------------
# ECR
# ------------------------------------------------------------------------------
output "ecr_repository_url" {
  description = "URL del repositorio ECR"
  value       = aws_ecr_repository.main.repository_url
}

output "ecr_repository_name" {
  description = "Nombre del repositorio ECR"
  value       = aws_ecr_repository.main.name
}

# ------------------------------------------------------------------------------
# Storage
# ------------------------------------------------------------------------------
output "efs_id" {
  description = "ID del EFS File System"
  value       = aws_efs_file_system.main.id
}

output "efs_dns_name" {
  description = "DNS name del EFS"
  value       = aws_efs_file_system.main.dns_name
}

output "efs_access_point_id" {
  description = "ID del EFS Access Point"
  value       = aws_efs_access_point.main.id
}

# ------------------------------------------------------------------------------
# IAM
# ------------------------------------------------------------------------------
output "ecs_task_execution_role_arn" {
  description = "ARN del ECS Task Execution Role"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ARN del ECS Task Role"
  value       = aws_iam_role.ecs_task_role.arn
}

# ------------------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------------------
output "cloudwatch_log_group_name" {
  description = "Nombre del CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.app.name
}

# ------------------------------------------------------------------------------
# Security
# ------------------------------------------------------------------------------
output "alb_security_group_id" {
  description = "ID del Security Group del ALB"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ID del Security Group de ECS Tasks"
  value       = aws_security_group.ecs_tasks.id
}

output "efs_security_group_id" {
  description = "ID del Security Group de EFS"
  value       = aws_security_group.efs.id
}

# ------------------------------------------------------------------------------
# Deployment Info
# ------------------------------------------------------------------------------
output "deployment_commands" {
  description = "Comandos para deployment"
  value       = <<-EOT
    # 1. Autenticar con ECR:
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.main.repository_url}
    
    # 2. Construir imagen:
    docker build -t ${aws_ecr_repository.main.name}:latest .
    
    # 3. Tagear imagen:
    docker tag ${aws_ecr_repository.main.name}:latest ${aws_ecr_repository.main.repository_url}:latest
    
    # 4. Push a ECR:
    docker push ${aws_ecr_repository.main.repository_url}:latest
    
    # 5. Forzar nuevo despliegue:
    aws ecs update-service --cluster ${aws_ecs_cluster.main.name} --service ${aws_ecs_service.app.name} --force-new-deployment --region ${var.aws_region}
  EOT
}
