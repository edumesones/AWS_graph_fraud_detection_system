# ==============================================================================
# Application Load Balancer
# ==============================================================================

# ------------------------------------------------------------------------------
# ALB Principal
# ------------------------------------------------------------------------------
resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection       = var.environment == "production" ? true : false
  enable_http2                     = true
  enable_cross_zone_load_balancing = true

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "alb"
    enabled = true
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-alb"
    }
  )
}

# ------------------------------------------------------------------------------
# Target Group
# ------------------------------------------------------------------------------
resource "aws_lb_target_group" "app" {
  name_prefix = "fd-"
  port        = local.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  deregistration_delay = 30

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400 # 24 horas
    enabled         = true
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-tg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# ------------------------------------------------------------------------------
# Listeners
# ------------------------------------------------------------------------------

# HTTP Listener (redirect a HTTPS si hay certificado)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = var.certificate_arn != "" ? "redirect" : "forward"

    dynamic "redirect" {
      for_each = var.certificate_arn != "" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }

    target_group_arn = var.certificate_arn == "" ? aws_lb_target_group.app.arn : null
  }
}

# HTTPS Listener (si se provee certificado)
resource "aws_lb_listener" "https" {
  count             = var.certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ------------------------------------------------------------------------------
# S3 Bucket para ALB Logs
# ------------------------------------------------------------------------------
resource "aws_s3_bucket" "alb_logs" {
  bucket_prefix = "${local.name_prefix}-alb-logs-"
  force_destroy = var.environment != "production"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-alb-logs"
    }
  )
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Política del bucket para permitir que ALB escriba logs
resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "logdelivery.elasticloadbalancing.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/*"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "logdelivery.elasticloadbalancing.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.alb_logs.arn
      }
    ]
  })
}
