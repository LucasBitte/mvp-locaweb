resource "aws_glue_catalog_database" "lake" { name = "${var.name}_lake" }
resource "aws_iam_role_policy" "catalog" {
  role = aws_iam_role.glue.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = [for p in ["bronze", "silver", "gold"] : "${aws_s3_bucket.lake.arn}/${p}/*"] },
    { Effect = "Allow", Action = ["glue:GetDatabase", "glue:GetTable", "glue:GetTables", "glue:CreateTable", "glue:UpdateTable", "glue:GetPartition", "glue:GetPartitions", "glue:BatchGetPartition", "glue:CreatePartition", "glue:BatchCreatePartition", "glue:UpdatePartition"], Resource = [
      "arn:aws:glue:${var.region}:${data.aws_caller_identity.current.account_id}:catalog",
      aws_glue_catalog_database.lake.arn,
      "arn:aws:glue:${var.region}:${data.aws_caller_identity.current.account_id}:table/${aws_glue_catalog_database.lake.name}/*"
    ] }
  ] })
}
resource "aws_glue_crawler" "lake" {
  name          = "${var.name}-lake"
  database_name = aws_glue_catalog_database.lake.name
  role          = aws_iam_role.glue.arn
  dynamic "s3_target" {
    for_each = toset(["bronze/public", "silver/staging", "gold/dw", "gold/ml"])
    content { path = "s3://${aws_s3_bucket.lake.id}/${s3_target.value}/" }
  }
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}
