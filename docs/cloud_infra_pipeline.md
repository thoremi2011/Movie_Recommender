# Cloud Deployment Pipeline for Movie Recommender

This is the cloud deployment pipeline I’ve set up for the **Movie Recommender** application using **AWS ECS (Fargate)** and **Terraform**.

## Pipeline Overview

The deployment follows these steps:

1. **Build and Push Docker Image**
2. **Deploy Infrastructure with Terraform**
3. **Launch ECS Service with Load Balancer**
4. **Monitor and Scale the Application**

## Step 1: Build and Push Docker Image

Before deploying, I first build the Docker image, tag it, and push it to **AWS ECR**.

```sh
# Authenticate Docker with AWS ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.eu-west-1.amazonaws.com

# Build the Docker image
docker build -t movie-recommender .

# Tag the image
docker tag movie-recommender:latest <aws_account_id>.dkr.ecr.eu-west-1.amazonaws.com/movie_recommender:latest

# Push the image to ECR
docker push <aws_account_id>.dkr.ecr.eu-west-1.amazonaws.com/movie_recommender:latest
```

## Step 2: Deploy Infrastructure with Terraform

Once the Docker image is in **ECR**, I provision the cloud infrastructure using **Terraform**.

```sh
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Plan deployment
terraform plan -out=tfplan

# Apply deployment
terraform apply tfplan
```

### Infrastructure Components
Terraform provisions the following AWS resources:
- **Amazon Elastic Container Registry (ECR)** to store container images
- **Amazon ECS (Fargate)** to run the application
- **IAM Roles and Policies** for ECS execution and task permissions
- **Application Load Balancer (ALB)** to route traffic
- **Security Groups** to enforce access control
- **AWS SSM Parameters** for configuration management
- **CloudWatch Logs** for logging and monitoring

## Step 3: Launch ECS Service with Load Balancer

Once Terraform provisions the infrastructure, it automatically deploys an **ECS service** that:
- Pulls the latest **Docker image** from **ECR**
- Runs on **Fargate** with predefined CPU and memory limits
- Registers itself with the **Application Load Balancer (ALB)**
- Uses AWS SSM parameters for dynamic configuration
- Logs events to **CloudWatch Logs**

### Verifying Deployment
After Terraform completes, I check if the ECS service is running:

```sh
aws ecs list-tasks --cluster movie-recommender-cluster
```

To check for errors, I look at the logs:

```sh
aws logs tail /ecs/movie-recommender-task --follow
```

## Step 4: Monitor and Scale the Application

### Auto Scaling Configuration
The application scales dynamically based on **CPU utilization** using **AWS Application Auto Scaling**.

```hcl
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 4
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
```

A simple policy scales the service up when CPU usage exceeds **80%**:

```hcl
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
    target_value = 80.0
  }
}
```

### Logs and Monitoring
- **CloudWatch Logs** captures logs from ECS tasks.
- **AWS WAF** prevents excessive API requests.
- **AWS Budgets** sends alerts if costs exceed predefined limits.

## Conclusion
This pipeline ensures that the Movie Recommender application is deployed in a **scalable, secure, and monitored** environment using AWS ECS, ECR, and Terraform.
