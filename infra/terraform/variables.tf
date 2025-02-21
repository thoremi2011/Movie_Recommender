variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "movie-recommender"
}

variable "vpc_id" {
  description = "The VPC ID where resources are created."
  type        = string
}

variable "alert_email" {
  description = "Email address for budget alerts"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 5
}

variable "waf_rate_limit" {
  description = "Number of requests allowed per 5 minutes per IP"
  type        = number
  default     = 100
}

variable "task_cpu" {
  description = "CPU units for the ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Memory for the ECS task in MB"
  type        = number
  default     = 2048
}

variable "public_subnets" {
  description = "List of public subnet IDs for the ALB."
  type        = list(string)
}

variable "container_port" {
  description = "Port exposed by the container"
  type        = number
  default     = 7860
}

variable "health_check_path" {
  description = "Path for ALB health check"
  type        = string
  default     = "/"
}

variable "health_check_interval" {
  description = "Interval for health checks (seconds)"
  type        = number
  default     = 30
}

variable "container_name" {
  description = "Name of the container in the task definition"
  type        = string
  default     = "movie-recommender"
}