resource "aws_security_group" "glue" {
  name   = "${var.name}-glue"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_vpc_security_group_ingress_rule" "glue_db" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = aws_security_group.glue.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id]
}
# Glue em VPC não recebe IP público. Endpoints privados substituem o NAT.
# Estes endpoints têm custo fixo: incluir no orçamento antes do apply.
resource "aws_vpc_endpoint" "services" {
  for_each            = toset(["secretsmanager", "logs"])
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.public[0].id]
  security_group_ids  = [aws_security_group.glue.id]
}
resource "aws_glue_connection" "network" {
  name            = "${var.name}-network"
  connection_type = "NETWORK"
  physical_connection_requirements {
    availability_zone      = aws_subnet.public[0].availability_zone
    subnet_id              = aws_subnet.public[0].id
    security_group_id_list = [aws_security_group.glue.id]
  }
}
resource "aws_iam_role" "glue" {
  name = "${var.name}-glue-export"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "glue.amazonaws.com" }
  }] })
}
resource "aws_iam_role_policy" "glue" {
  role = aws_iam_role.glue.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.lake.arn },
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.lake.arn}/jobs/*" },
    { Effect = "Allow", Action = ["s3:PutObject"], Resource = [for p in ["bronze", "silver", "gold", "manifests"] : "${aws_s3_bucket.lake.arn}/${p}/*"] },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = var.glue_reader_secret_arn },
    { Effect = "Allow", Action = ["ec2:CreateNetworkInterface", "ec2:DeleteNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DescribeVpcEndpoints", "ec2:DescribeRouteTables", "ec2:DescribeSubnets", "ec2:DescribeSecurityGroups", "ec2:DescribeVpcAttribute"], Resource = "*" },
    { Effect = "Allow", Action = ["ec2:CreateTags", "ec2:DeleteTags"], Resource = "arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:network-interface/*", Condition = { "ForAllValues:StringEquals" = { "aws:TagKeys" = ["aws-glue-service-resource"] } } },
    { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/*" }
  ] })
}
resource "aws_s3_object" "export" {
  bucket = aws_s3_bucket.lake.id
  key    = "jobs/export_lake.py"
  source = "${path.module}/../cloud/export_lake.py"
  etag   = filemd5("${path.module}/../cloud/export_lake.py")
}
resource "aws_s3_object" "db" {
  bucket = aws_s3_bucket.lake.id
  key    = "jobs/db.py"
  source = "${path.module}/../etl/db.py"
  etag   = filemd5("${path.module}/../etl/db.py")
}
resource "aws_glue_job" "export" {
  name         = "${var.name}-rds-to-s3"
  role_arn     = aws_iam_role.glue.arn
  max_capacity = 0.0625
  timeout      = 30
  max_retries  = 0
  connections  = [aws_glue_connection.network.name]
  execution_property { max_concurrent_runs = 1 }
  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_bucket.lake.id}/${aws_s3_object.export.key}"
  }
  default_arguments = {
    "--library-set" = "analytics"
    "--bucket"      = aws_s3_bucket.lake.id
    "--secret-id"   = var.glue_reader_secret_arn
  }
}
