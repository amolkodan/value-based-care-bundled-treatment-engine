project_name         = "vbc-bundled-engine"
environment          = "dev"
aws_region           = "us-east-1"
db_password          = "CHANGE_ME_DEV_PASSWORD"
container_image      = "111111111111.dkr.ecr.us-east-1.amazonaws.com/vbc-claims:dev"
s3_data_bucket_name  = "vbc-bundled-engine-dev-data"
desired_count        = 1
db_instance_class    = "db.t4g.micro"
db_allocated_storage = 50

