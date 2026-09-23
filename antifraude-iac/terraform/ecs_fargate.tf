# ==============================================================================
# Amazon ECS Fargate - Cluster, Task Definition, Service & Auto Scaling
# ==============================================================================

# ------------------------------------------------------------------------------
# CloudWatch Log Group
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 30

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-logs"
    }
  )
}

# ------------------------------------------------------------------------------
# ECS Cluster
# ------------------------------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-cluster"
    }
  )
}
# ------------------------------------------------------------------------------
# ECS Task Definition
# ------------------------------------------------------------------------------
resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name_prefix}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  # Volumen EFS para persistencia
  volume {
    name = "efs-storage"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.main.id
      root_directory     = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.main.id
        iam             = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = local.container_name
      image     = "${aws_ecr_repository.main.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = local.container_port
          protocol      = "tcp"
        }
      ]

      # Montaje EFS
      mountPoints = [
        {
          sourceVolume  = "efs-storage"
          containerPath = local.efs_mount_path
          readOnly      = false
        }
      ]

      environment = [
        {
          name  = "GRADIO_SERVER_NAME"
          value = "0.0.0.0"
        },
        {
          name  = "GRADIO_SERVER_PORT"
          value = tostring(local.container_port)
        },
        {
          name  = "GRADIO_ANALYTICS_ENABLED"
          value = "False"
        },
        {
          name  = "NO_PROXY"
          value = "127.0.0.1,localhost"
        },
        {
          name  = "MPLCONFIGDIR"
          value = "/tmp/matplotlib"
        },
        {
          name  = "HOME"
          value = "/app"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "LOG_LEVEL"
          value = var.environment == "production" ? "INFO" : "DEBUG"
        },
        {
          name  = "PERSISTENT_DATA_PATH"
          value = local.efs_mount_path
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:7860/\", timeout=5)' || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 40
      }

      # Límites de recursos
      ulimits = [
        {
          name      = "nofile"
          softLimit = 65536
          hardLimit = 65536
        }
      ]
    }
  ])

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-task-def"
    }
  )
}

# ------------------------------------------------------------------------------
# ECS Service
# ------------------------------------------------------------------------------
resource "aws_ecs_service" "app" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  
  platform_version = "LATEST"
  
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = local.container_name
    container_port   = local.container_port
  }
  
  # Despliegue controlado
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100
  
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Habilitar ECS Exec para debugging
  enable_execute_command = var.environment != "production"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-service"
    }
  )

  depends_on = [
    aws_lb_listener.http,
    aws_iam_role_policy.ecs_task_execution_ecr,
    aws_iam_role_policy.ecs_task_efs_access
  ]

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# ==============================================================================
# AUTO SCALING - Target Tracking con CPU y Memoria
# ==============================================================================

# ------------------------------------------------------------------------------
# Auto Scaling Target
# ------------------------------------------------------------------------------
resource "aws_appautoscaling_target" "ecs_service" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# ------------------------------------------------------------------------------
# Target Tracking Policy - CPU Utilization
# ------------------------------------------------------------------------------
resource "aws_appautoscaling_policy" "ecs_cpu" {
  name               = "${local.name_prefix}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = var.cpu_target_value
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# ------------------------------------------------------------------------------
# Target Tracking Policy - Memory Utilization
# ------------------------------------------------------------------------------
resource "aws_appautoscaling_policy" "ecs_memory" {
  name               = "${local.name_prefix}-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_service.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_service.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_service.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }

    target_value       = var.memory_target_value
    scale_in_cooldown  = var.scale_in_cooldown
    scale_out_cooldown = var.scale_out_cooldown
  }
}

# ------------------------------------------------------------------------------
# CloudWatch Alarms para Monitoring
# ------------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${local.name_prefix}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors ECS CPU utilization"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "memory_high" {
  alarm_name          = "${local.name_prefix}-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "90"
  alarm_description   = "This metric monitors ECS memory utilization"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }

  tags = local.common_tags
}
