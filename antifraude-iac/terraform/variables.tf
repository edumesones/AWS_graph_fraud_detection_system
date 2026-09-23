# ==============================================================================
# Variables de Configuración - Infraestructura AWS Fraud Detection
# ==============================================================================

# ------------------------------------------------------------------------------
# General
# ------------------------------------------------------------------------------
variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "fraud-detection"
}

variable "environment" {
  description = "Ambiente de despliegue"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "El ambiente debe ser: dev, staging o production"
  }
}

variable "aws_region" {
  description = "Región AWS para el despliegue"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Tags comunes para todos los recursos"
  type        = map(string)
  default = {
    Project   = "fraud-detection"
    ManagedBy = "terraform"
    Team      = "data-science"
  }
}

# ------------------------------------------------------------------------------
# Networking
# ------------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block para la VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Zonas de disponibilidad"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# ------------------------------------------------------------------------------
# ECS Fargate
# ------------------------------------------------------------------------------
variable "container_cpu" {
  description = "CPU para la tarea de Fargate (1024 = 1 vCPU)"
  type        = number
  default     = 4096 # 4 vCPU para procesamiento de grafos
}

variable "container_memory" {
  description = "Memoria para la tarea de Fargate (MB)"
  type        = number
  default     = 8192 # 8 GB para grafos en memoria
}

variable "desired_count" {
  description = "Número inicial de tareas"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Capacidad mínima de auto scaling"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Capacidad máxima de auto scaling"
  type        = number
  default     = 10
}

# ------------------------------------------------------------------------------
# Auto Scaling
# ------------------------------------------------------------------------------
variable "cpu_target_value" {
  description = "Target de CPU para auto scaling (%)"
  type        = number
  default     = 70
}

variable "memory_target_value" {
  description = "Target de memoria para auto scaling (%)"
  type        = number
  default     = 80
}

variable "scale_in_cooldown" {
  description = "Cooldown para scale in (segundos)"
  type        = number
  default     = 300
}

variable "scale_out_cooldown" {
  description = "Cooldown para scale out (segundos)"
  type        = number
  default     = 60
}

# ------------------------------------------------------------------------------
# Domain & SSL
# ------------------------------------------------------------------------------
variable "domain_name" {
  description = "Nombre de dominio para la aplicación (opcional)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ARN del certificado ACM para HTTPS (opcional)"
  type        = string
  default     = ""
}

# ------------------------------------------------------------------------------
# Storage
# ------------------------------------------------------------------------------
variable "efs_performance_mode" {
  description = "Modo de performance de EFS"
  type        = string
  default     = "generalPurpose"
  validation {
    condition     = contains(["generalPurpose", "maxIO"], var.efs_performance_mode)
    error_message = "El modo debe ser generalPurpose o maxIO"
  }
}
