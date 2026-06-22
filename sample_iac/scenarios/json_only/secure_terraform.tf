resource "aws_security_group" "web" {
  name = "web-access"

  ingress {
    description = "HTTPS from the private network"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

