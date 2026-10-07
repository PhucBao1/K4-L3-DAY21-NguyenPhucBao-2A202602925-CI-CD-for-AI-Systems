# EC2 chay income-api (Buoc 2). Bucket da tao truoc bang CLI, o day chi tham chieu theo ten.
# Dung:  terraform init && terraform apply     Don dep:  terraform destroy

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  default = "us-east-1"
}

variable "bucket" {
  default = "income-lab-623900187672"
}

variable "ssh_public_key_path" {
  default = "~/.ssh/income_deploy.pub"
}

provider "aws" {
  region = var.region
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_key_pair" "deploy" {
  key_name   = "income-deploy"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

# Cong 22 mo cho moi IP vi IP cua GitHub Actions runner thay doi lien tuc.
resource "aws_security_group" "api" {
  name = "income-api"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# VM chi duoc doc model, khong can access key tren may.
resource "aws_iam_role" "api" {
  name = "income-api-ec2"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "read_model" {
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "s3:GetObject", Resource = "arn:aws:s3:::${var.bucket}/artifacts/*" }]
  })
}

resource "aws_iam_instance_profile" "api" {
  name = "income-api-ec2"
  role = aws_iam_role.api.name
}

resource "aws_instance" "api" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.small"
  key_name               = aws_key_pair.deploy.key_name
  vpc_security_group_ids = [aws_security_group.api.id]
  iam_instance_profile   = aws_iam_instance_profile.api.name

  # Cai moi truong + systemd service (buoc 2.5 - 2.7). Service chi enable, chua start:
  # model chua co tren S3 cho den khi pipeline chay lan dau; job Release se restart no.
  user_data = <<-EOF
    #!/bin/bash
    set -e
    apt-get update
    apt-get install -y python3-pip
    pip3 install fastapi==0.111.0 uvicorn==0.29.0 scikit-learn==1.4.2 joblib==1.4.2 boto3
    mkdir -p /home/ubuntu/models /home/ubuntu/src
    echo '${base64encode(file("${path.module}/../src/serve.py"))}' | base64 -d > /home/ubuntu/src/serve.py
    chown -R ubuntu:ubuntu /home/ubuntu/models /home/ubuntu/src
    cat > /etc/systemd/system/income-api.service <<UNIT
    [Unit]
    Description=Income Model Inference Server
    After=network.target

    [Service]
    User=ubuntu
    WorkingDirectory=/home/ubuntu
    Environment="ARTIFACT_BUCKET=${var.bucket}"
    Environment="AWS_DEFAULT_REGION=${var.region}"
    ExecStart=/usr/bin/python3 /home/ubuntu/src/serve.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    UNIT
    systemctl daemon-reload
    systemctl enable income-api
  EOF

  tags = {
    Name = "income-api"
  }
}

output "public_ip" {
  value = aws_instance.api.public_ip
}
