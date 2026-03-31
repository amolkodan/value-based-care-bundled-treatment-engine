output "vpc_id" {
  value = aws_vpc.main.id
}

output "alb_dns_name" {
  value = aws_lb.api.dns_name
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.api.name
}

output "s3_data_bucket" {
  value = aws_s3_bucket.data_bucket.id
}

