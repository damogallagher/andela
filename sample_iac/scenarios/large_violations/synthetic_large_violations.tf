resource "aws_security_group" "synthetic_open_ssh_01" {
  name = "synthetic-open-ssh-01"

  ingress {
    description = "Synthetic SSH exposure 01"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "synthetic_open_ssh_02" {
  name = "synthetic-open-ssh-02"

  ingress {
    description = "Synthetic SSH exposure 02"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "synthetic_open_ssh_03" {
  name = "synthetic-open-ssh-03"

  ingress {
    description = "Synthetic SSH exposure 03"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "synthetic_open_ssh_04" {
  name = "synthetic-open-ssh-04"

  ingress {
    description = "Synthetic SSH exposure 04"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "synthetic_open_ssh_05" {
  name = "synthetic-open-ssh-05"

  ingress {
    description = "Synthetic SSH exposure 05"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "synthetic_open_ssh_06" {
  name = "synthetic-open-ssh-06"

  ingress {
    description = "Synthetic SSH exposure 06"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "synthetic_public_bucket_01" {
  bucket = "andela-synthetic-public-01"
  acl    = "public-read"
}

resource "aws_s3_bucket" "synthetic_public_bucket_02" {
  bucket = "andela-synthetic-public-02"
  acl    = "public-read"
}

resource "aws_s3_bucket" "synthetic_public_bucket_03" {
  bucket = "andela-synthetic-public-03"
  acl    = "public-read"
}

resource "aws_s3_bucket" "synthetic_public_bucket_04" {
  bucket = "andela-synthetic-public-04"
  acl    = "public-read"
}

resource "aws_s3_bucket" "synthetic_public_bucket_05" {
  bucket = "andela-synthetic-public-05"
  acl    = "public-read"
}

resource "aws_s3_bucket" "synthetic_public_bucket_06" {
  bucket = "andela-synthetic-public-06"
  acl    = "public-read"
}

resource "aws_db_instance" "synthetic_unencrypted_db_01" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = false
}

resource "aws_db_instance" "synthetic_unencrypted_db_02" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = false
}

resource "aws_db_instance" "synthetic_unencrypted_db_03" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = false
}

resource "aws_db_instance" "synthetic_unencrypted_db_04" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = false
}

resource "aws_db_instance" "synthetic_unencrypted_db_05" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = false
}

resource "aws_db_instance" "synthetic_unencrypted_db_06" {
  allocated_storage = 20
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  storage_encrypted = false
}

resource "aws_s3_bucket_versioning" "synthetic_suspended_versioning_01" {
  bucket = aws_s3_bucket.synthetic_public_bucket_01.id

  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_versioning" "synthetic_suspended_versioning_02" {
  bucket = aws_s3_bucket.synthetic_public_bucket_02.id

  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_versioning" "synthetic_suspended_versioning_03" {
  bucket = aws_s3_bucket.synthetic_public_bucket_03.id

  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_versioning" "synthetic_suspended_versioning_04" {
  bucket = aws_s3_bucket.synthetic_public_bucket_04.id

  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_versioning" "synthetic_suspended_versioning_05" {
  bucket = aws_s3_bucket.synthetic_public_bucket_05.id

  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_versioning" "synthetic_suspended_versioning_06" {
  bucket = aws_s3_bucket.synthetic_public_bucket_06.id

  versioning_configuration {
    status = "Suspended"
  }
}
