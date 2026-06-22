resource "aws_s3_bucket" "reports" {
  bucket = "andela-risk-report-demo"
  acl    = "public-read"
}

