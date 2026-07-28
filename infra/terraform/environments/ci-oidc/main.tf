/**
 * Stack Terraform — CI OIDC (R4-F17).
 *
 * Provisiona OIDC provider + IAM Role para GitHub Actions.
 * Aplicar uma vez por conta AWS (não faz parte do pipeline CDN).
 */

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

module "github_oidc" {
  source = "../../modules/github-oidc"

  github_org           = var.github_org
  github_repo          = var.github_repo
  github_ref_filter    = var.github_ref_filter
  role_name            = var.role_name
  create_oidc_provider = var.create_oidc_provider
  state_bucket         = var.state_bucket
  lock_table           = var.lock_table
  cdn_bucket_names     = var.cdn_bucket_names
  tags                 = var.tags
}

output "aws_role_arn" {
  description = "Valor para o secret GitHub AWS_ROLE_ARN."
  value       = module.github_oidc.role_arn
}

output "oidc_provider_arn" {
  value = module.github_oidc.oidc_provider_arn
}
