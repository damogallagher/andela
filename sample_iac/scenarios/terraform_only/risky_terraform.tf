resource "aws_s3_bucket" "reports" {
  bucket = "andela-risk-report-demo"
  acl    = "public-read"
}

resource "aws_db_instance" "orders" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = false
}

