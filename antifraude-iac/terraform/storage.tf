# ==============================================================================
# Amazon EFS - Persistent Storage para Logs y Exports
# ==============================================================================

# ------------------------------------------------------------------------------
# EFS File System
# ------------------------------------------------------------------------------
resource "aws_efs_file_system" "main" {
  creation_token   = "${local.name_prefix}-efs"
  performance_mode = var.efs_performance_mode
  throughput_mode  = "bursting"
  encrypted        = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle_policy {
    transition_to_primary_storage_class = "AFTER_1_ACCESS"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-efs"
    }
  )
}

# ------------------------------------------------------------------------------
# EFS Mount Targets (uno por AZ para HA)
# ------------------------------------------------------------------------------
resource "aws_efs_mount_target" "main" {
  count           = length(var.availability_zones)
  file_system_id  = aws_efs_file_system.main.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}

# ------------------------------------------------------------------------------
# EFS Access Point (para mejor control de permisos)
# ------------------------------------------------------------------------------
resource "aws_efs_access_point" "main" {
  file_system_id = aws_efs_file_system.main.id

  posix_user {
    uid = 1001 # Mismo UID que el usuario 'appuser' del Dockerfile
    gid = 1001
  }

  root_directory {
    path = "/data"
    creation_info {
      owner_uid   = 1001
      owner_gid   = 1001
      permissions = "755"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-efs-access-point"
    }
  )
}

# ------------------------------------------------------------------------------
# Backup Policy para EFS
# ------------------------------------------------------------------------------
resource "aws_efs_backup_policy" "main" {
  file_system_id = aws_efs_file_system.main.id

  backup_policy {
    status = "ENABLED"
  }
}
