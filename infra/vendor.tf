resource "aws_s3_object" "dotenv" {
  bucket = aws_s3_bucket.lake.id
  key    = "jobs/python_dotenv-1.0.1-py3-none-any.whl"
  source = "${path.module}/.artifacts/python_dotenv-1.0.1-py3-none-any.whl"
  etag   = filemd5("${path.module}/.artifacts/python_dotenv-1.0.1-py3-none-any.whl")
}
