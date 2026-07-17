terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "coreflow_cdn" {
  source = "../../modules/coreflow-cdn"

  aws_region               = var.aws_region
  bucket_name              = var.bucket_name
  cdn_prefix               = var.cdn_prefix
  cloudfront_aliases       = var.cloudfront_aliases
  cloudfront_price_class   = var.cloudfront_price_class
  well_known_cache_seconds = var.well_known_cache_seconds
  tenant_behaviors         = var.tenant_behaviors
  tags                     = var.tags
}
