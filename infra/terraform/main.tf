provider "aws" {
  region = "eu-west-1"
}

# ECR Repository
resource "aws_ecr_repository" "movie_recommender" {
  name                 = "movie_recommender"
  image_tag_mutability = "MUTABLE"
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "movie-recommender-cluster"
}

# IAM Role para ECS
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "movie-recommender-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Attach policy for ECR access
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "movie-recommender-task"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = var.task_cpu
  memory                  = var.task_memory
  execution_role_arn      = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "movie-recommender"
      image = "${aws_ecr_repository.movie_recommender.repository_url}:latest"
      
      environment = [
        {
          name  = "USE_SSM",
          value = "true"
        },
        {
          name  = "ENVIRONMENT",
          value = var.environment
        },
        {
          name  = "MOVIES_CSV_PATH",
          value = "s3://movie-recommender-data-dev/data/processed/movies_processed.csv"
        }
      ]
      
      portMappings = [
        {
          containerPort = 7860
          hostPort      = 7860
          protocol      = "tcp"
        },
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/movie-recommender-task"
          "awslogs-region"        = "eu-west-1"
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# ECS Service
resource "aws_ecs_service" "app" {
  name            = "movie-recommender-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # Load Balancer Configuration
  load_balancer {
    target_group_arn = aws_lb_target_group.movie_recommender_tg.arn
    container_name   = "movie-recommender"  # Debe coincidir con el nombre en la task definition
    container_port   = var.container_port
  }

  network_configuration {
    subnets          = var.public_subnets
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = true
  }

  # Ensure ALB listener is created before the service
  depends_on = [aws_lb_listener.movie_recommender_listener]
}

# Configuración de Auto Scaling (comentada)
/*
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 4
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_policy_cpu" {
  name               = "cpu-auto-scaling"
  policy_type       = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 80.0  # Escala cuando CPU > 80%
  }
}
*/

# Security Group for the application (ECS Tasks)
resource "aws_security_group" "app" {
  name        = "${var.app_name}-app-sg"
  description = "Security group for the ECS tasks"
  vpc_id      = var.vpc_id

  # Allow incoming traffic from ALB to Gradio port
  ingress {
    from_port       = 7860
    to_port         = 7860
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow incoming traffic from ALB to FastAPI port
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow all outgoing traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-app-sg"
    Environment = var.environment
  }
}

# Security Group para el ALB
resource "aws_security_group" "alb" {
  name        = "${var.app_name}-alb-sg"
  description = "Security group for the ALB"
  vpc_id      = var.vpc_id

  # Allow incoming HTTP traffic from Internet
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow incoming Gradio traffic from Internet
  ingress {
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outgoing traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-alb-sg"
    Environment = var.environment
  }
}

# AWS Budget
resource "aws_budgets_budget" "cost" {
  name              = "movie-recommender-budget"
  budget_type       = "COST"
  limit_amount      = "5"
  limit_unit        = "USD"    # AWS solo acepta USD
  time_period_start = "2024-02-19_00:00"
  time_unit         = "DAILY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}

# WAF (Web Application Firewall) para rate limiting
resource "aws_wafv2_web_acl" "main" {
  name        = "movie-recommender-waf"
  description = "WAF with rate limiting rules"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "RateLimit"
    priority = 1

    action {
      block {}    # Bloquea cuando se excede el límite
    }

    statement {
      rate_based_statement {
        limit              = var.waf_rate_limit    # Límite de peticiones por 5 minutos por IP
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "RateLimitMetric"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "WAFMetric"
    sampled_requests_enabled  = true
  }
}

# S3 Bucket para almacenamiento de datos
resource "aws_s3_bucket" "data_storage" {
  bucket = "movie-recommender-data-${var.environment}"
}

# Create S3 folder structure (optional, but recommended)
resource "aws_s3_object" "folders" {
  for_each = toset([
    "data/",
    "data/embeddings/",
    "data/processed/",
    "models/",
    "models/onnx/"
  ])
  
  bucket = aws_s3_bucket.data_storage.id
  key    = each.value
  content_type = "application/x-directory"
  content = ""          # Contenido vacío para Windows
}

# Bucket encryption configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "embeddings" {
  bucket = aws_s3_bucket.data_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# IAM policy for ECS to access the bucket
resource "aws_iam_role_policy_attachment" "ecs_s3_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# Create S3 access policy
resource "aws_iam_policy" "s3_access" {
  name = "movie-recommender-s3-access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_storage.arn,
          "${aws_s3_bucket.data_storage.arn}/*"
        ]
      }
    ]
  })
}

# SSM Parameter para la configuración de modelos
resource "aws_ssm_parameter" "models_config" {
  name  = "/${var.environment}/movie-recommender/models-config"
  type  = "String"
  value = "{ }"  # Valor inicial vacío
  lifecycle {
    ignore_changes = [value]
  }
}

# Add permissions to ECS role to read SSM
resource "aws_iam_role_policy_attachment" "ecs_ssm_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}

# Create CloudWatch Logs access policy
resource "aws_iam_policy" "cloudwatch_logs" {
  name = "movie-recommender-cloudwatch-logs"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policy to ECS role
resource "aws_iam_role_policy_attachment" "ecs_cloudwatch_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.cloudwatch_logs.arn
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/movie-recommender-task"
  retention_in_days = 30
}

# IAM Role para la tarea
resource "aws_iam_role" "ecs_task_role" {
  name = "movie-recommender-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Policy for task role
resource "aws_iam_role_policy" "ecs_task_role_policy" {
  name = "movie-recommender-task-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::movie-recommender-data-dev/*",
          "arn:aws:s3:::movie-recommender-data-dev"
        ]
      }
    ]
  })
}

resource "aws_lb" "movie_recommender_alb" {
  name               = "movie-recommender-alb"
  load_balancer_type = "application"
  internal           = false
  subnets            = var.public_subnets
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "movie_recommender_tg" {
  name     = "movie-recommender-tg"
  port     = var.container_port
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    path                = var.health_check_path
    interval            = var.health_check_interval
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
    matcher             = "200-299"
  }
}

resource "aws_lb_listener" "movie_recommender_listener" {
  load_balancer_arn = aws_lb.movie_recommender_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.movie_recommender_tg.arn
  }
}

# Add SSM read permissions to task role
resource "aws_iam_role_policy_attachment" "ecs_task_ssm" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
} 
