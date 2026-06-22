resource "aws_security_group" "app" {
  name = "app-access"

  ingress {
    description = "Application traffic from private subnets"
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = ["10.10.0.0/16"]
  }
}

resource "aws_db_instance" "orders" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = true
}

