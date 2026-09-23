# ==============================================================================
# Main Terraform Configuration - Fraud Detection AWS Infrastructure
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Configurar backend S3 para estado remoto (descomentar y configurar)
  # backend "s3" {
  #   bucket         = "fraud-detection-terraform-state"
  #   key            = "production/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

# ------------------------------------------------------------------------------
# Provider AWS
# ------------------------------------------------------------------------------
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      var.tags,
      {
        Environment = var.environment
        Terraform   = "true"
      }
    )
  }
}

# ------------------------------------------------------------------------------
# Data Sources
# ------------------------------------------------------------------------------
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# ------------------------------------------------------------------------------
# Local Variables
# ------------------------------------------------------------------------------
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    var.tags,
    {
      Name        = local.name_prefix
      Environment = var.environment
    }
  )

  container_name = "fraud-detection-app"
  container_port = 7860

  # EFS mount path en el contenedor
  efs_mount_path = "/app/persistent"
}
