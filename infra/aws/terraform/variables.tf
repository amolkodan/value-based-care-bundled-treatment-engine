variable "project_name" {
  type        = string
  description = "Project identifier used for resource naming."
}

variable "environment" {
  type        = string
  description = "Environment name (dev/stage/prod)."
}

variable "aws_region" {
  type        = string
  description = "AWS region."
  default     = "us-east-1"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.40.0.0/16"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  default     = ["10.40.0.0/24", "10.40.1.0/24"]
}

variable "private_subnet_cidrs" {
  type        = list(string)
  default     = ["10.40.10.0/24", "10.40.11.0/24"]
}

variable "db_name" {
  type        = string
  default     = "vbc_claims"
}

variable "db_username" {
  type        = string
  default     = "vbc"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "RDS master password. Use CI secrets or Terraform Cloud variables."
}

variable "db_instance_class" {
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type        = number
  default     = 50
}

variable "container_image" {
  type        = string
  description = "ECR image URI for API service."
}

variable "container_port" {
  type        = number
  default     = 8001
}

variable "desired_count" {
  type        = number
  default     = 1
}

variable "cpu" {
  type        = number
  default     = 512
}

variable "memory" {
  type        = number
  default     = 1024
}

variable "s3_data_bucket_name" {
  type        = string
  description = "S3 bucket for data drops/artifacts."
}

