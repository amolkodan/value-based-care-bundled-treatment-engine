project_name         = "vbc-bundled-engine"
environment          = "stage"
aws_region           = "us-east-1"
db_password          = "CHANGE_ME_STAGE_PASSWORD"
container_image      = "111111111111.dkr.ecr.us-east-1.amazonaws.com/vbc-claims:stage"
s3_data_bucket_name  = "vbc-bundled-engine-stage-data"
desired_count        = 2
db_instance_class    = "db.t4g.small"
db_allocated_storage = 100

