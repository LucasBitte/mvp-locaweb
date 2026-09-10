output "rds_host" { value = aws_db_instance.main.address }
output "admin_secret_arn" { value = aws_db_instance.main.master_user_secret[0].secret_arn }
output "lake_bucket" { value = aws_s3_bucket.lake.id }
output "glue_job" { value = aws_glue_job.export.name }
