# SAFWAAN AI STUDIO - Infrastructure as Code
# Multi-cloud deployment with Crossplane and Terraform

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.31"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.12"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket = "safwaan-terraform-state"
    key    = "safwaan-ai-studio/terraform.tfstate"
    region = "us-east-1"
  }
}

# AWS Provider
provider "aws" {
  region = var.aws_region

  assume_role {
    role_arn = var.aws_assume_role_arn
  }
}

# Google Cloud Provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Azure Provider
provider "azurerm" {
  features {}

  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

# Kubernetes Provider (for Crossplane)
provider "kubernetes" {
  config_path = "~/.kube/config"
}

# Helm Provider
provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

# Variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_assume_role_arn" {
  description = "AWS IAM role to assume"
  type        = string
}

variable "gcp_project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "azure_tenant_id" {
  description = "Azure tenant ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

# Crossplane Installation
resource "helm_release" "crossplane" {
  name             = "crossplane"
  repository       = "https://charts.crossplane.io/stable"
  chart            = "crossplane"
  namespace        = "crossplane-system"
  create_namespace = true

  set {
    name  = "args"
    value = "{--enable-external-secret-stores}"
  }
}

# AWS EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "safwaan-${var.environment}"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    gpu_nodes = {
      instance_types = ["g4dn.xlarge", "g4dn.2xlarge", "g4dn.4xlarge", "g5.xlarge"]
      min_size       = 2
      max_size       = 12
      desired_size   = 4

      labels = {
        "safwaan.ai/node-type" = "gpu"
        "safwaan.ai/capability" = "premium"
        "safwaan.ai/workflow" = "video-pipeline"
      }

      taints = [{
        key    = "nvidia.com/gpu"
        value  = "present"
        effect = "NoSchedule"
      }]
    }

    cpu_nodes = {
      instance_types = ["c5.2xlarge", "c5.4xlarge"]
      min_size       = 3
      max_size       = 20
      desired_size   = 6

      labels = {
        "safwaan.ai/node-type" = "cpu"
        "safwaan.ai/workflow" = "orchestration"
      }
    }
    
    workflow_nodes = {
      instance_types = ["m5.2xlarge"]
      min_size       = 2
      max_size       = 5
      desired_size   = 2

      labels = {
        "safwaan.ai/node-type" = "workflow"
        "safwaan.ai/capability" = "n8n"
      }
    }
  }

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

# VPC for EKS
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "safwaan-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = false

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

# S3 Bucket for storage
resource "aws_s3_bucket" "safwaan_media" {
  bucket = "safwaan-media-${var.environment}"

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

resource "aws_s3_bucket_versioning" "safwaan_media" {
  bucket = aws_s3_bucket.safwaan_media.id
  versioning_configuration {
    status = "Enabled"
  }
}

# RDS PostgreSQL Database
resource "aws_db_instance" "safwaan_db" {
  identifier             = "safwaan-${var.environment}"
  engine                 = "postgres"
  engine_version         = "16.1"
  instance_class         = "db.r6g.2xlarge"
  allocated_storage      = 100
  max_allocated_storage  = 1000
  storage_type           = "gp3"
  storage_encrypted      = true

  db_name  = "safwaan"
  username = "safwaan_admin"
  password = random_password.db_password.result

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.safwaan.name

  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  multi_az               = true
  skip_final_snapshot    = false
  final_snapshot_identifier = "safwaan-${var.environment}-final"

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Redis Cluster
resource "aws_elasticache_cluster" "safwaan_redis" {
  cluster_id           = "safwaan-${var.environment}"
  engine               = "redis"
  node_type            = "cache.r6g.xlarge"
  num_cache_nodes      = 2
  parameter_group_name = "default.redis7.cluster.on"
  port                 = 6379

  security_group_ids = [aws_security_group.redis.id]
  subnet_group_name  = aws_elasticache_subnet_group.safwaan.name

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

# Security Groups
resource "aws_security_group" "rds" {
  name_prefix = "safwaan-rds-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "safwaan-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

# Subnet Groups
resource "aws_db_subnet_group" "safwaan" {
  name       = "safwaan-${var.environment}"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

resource "aws_elasticache_subnet_group" "safwaan" {
  name       = "safwaan-${var.environment}"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

# CloudFront CDN
resource "aws_cloudfront_distribution" "safwaan" {
  origin {
    domain_name = aws_s3_bucket.safwaan_media.bucket_regional_domain_name
    origin_id   = "safwaan-s3-origin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.safwaan.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "safwaan-s3-origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.safwaan.arn
    ssl_support_method  = "sni-only"
  }

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

resource "aws_cloudfront_origin_access_identity" "safwaan" {
  comment = "Safwaan AI Studio CDN Origin Access Identity"
}

# ACM Certificate
resource "aws_acm_certificate" "safwaan" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = [
    "*.${var.domain_name}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

# Google Cloud Storage (Multi-cloud)
resource "google_storage_bucket" "safwaan_backup" {
  name          = "safwaan-backup-${var.environment}"
  location      = var.gcp_region
  storage_class = "STANDARD"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# Azure Storage Account (Multi-cloud)
resource "azurerm_storage_account" "safwaan" {
  name                     = "safwaan${var.environment}"
  resource_group_name      = azurerm_resource_group.safwaan.name
  location                 = azurerm_resource_group.safwaan.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

resource "azurerm_resource_group" "safwaan" {
  name     = "safwaan-${var.environment}"
  location = "East US"

  tags = {
    Environment = var.environment
    Application = "safwaan-ai-studio"
  }
}

# Outputs
output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = aws_db_instance.safwaan_db.endpoint
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_cluster.safwaan_redis.cache_nodes[0].address
}

output "s3_bucket_name" {
  description = "S3 bucket for media storage"
  value       = aws_s3_bucket.safwaan_media.bucket
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain"
  value       = aws_cloudfront_distribution.safwaan.domain_name
}

output "gcp_bucket_name" {
  description = "GCP bucket for backups"
  value       = google_storage_bucket.safwaan_backup.name
}

output "azure_storage_account" {
  description = "Azure storage account name"
  value       = azurerm_storage_account.safwaan.name
}