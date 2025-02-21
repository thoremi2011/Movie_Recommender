output "ecr_repository_url" {
  value = aws_ecr_repository.movie_recommender.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "security_group_id" {
  value = aws_security_group.app.id
  description = "The ID of the security group"
}

output "ecs_role_arn" {
  value = aws_iam_role.ecs_task_execution_role.arn
  description = "IAM role ARN for ECS"
}

output "service_public_ip" {
  value = aws_ecs_service.app.network_configuration[0].assign_public_ip
  description = "Public IP of the ECS service"
}

output "alb_dns_name" {
  description = "DNS name of the ALB"
  value       = aws_lb.movie_recommender_alb.dns_name
}

output "alb_security_group_id" {
  value       = aws_security_group.alb.id
  description = "The ID of the ALB security group"
}

output "alb_target_group_arn" {
  description = "ARN of the ALB Target Group"
  value       = aws_lb_target_group.movie_recommender_tg.arn
}

output "alb_zone_id" {
  description = "The zone_id of the ALB to be used in DNS records"
  value       = aws_lb.movie_recommender_alb.zone_id
}

output "alb_arn" {
  description = "ARN of the ALB"
  value       = aws_lb.movie_recommender_alb.arn
}