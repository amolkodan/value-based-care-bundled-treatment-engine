project_name         = "vbc-bundled-engine"
environment          = "prod"
aws_region           = "us-east-1"
db_password          = "CHANGE_ME_PROD_PASSWORD"
container_image      = "111111111111.dkr.ecr.us-east-1.amazonaws.com/vbc-claims:prod"
s3_data_bucket_name  = "vbc-bundled-engine-prod-data"
desired_count        = 3
db_instance_class    = "db.r6g.large"
db_allocated_storage = 200

