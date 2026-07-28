variable "aws_region" {
  description = "Região AWS do provider."
  type        = string
  default     = "us-east-1"
}

variable "github_org" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "github_ref_filter" {
  type    = string
  default = "*"
}

variable "role_name" {
  type    = string
  default = "coreflow-github-actions"
}

variable "create_oidc_provider" {
  type    = bool
  default = true
}

variable "state_bucket" {
  type    = string
  default = "coreflow-terraform-state"
}

variable "lock_table" {
  type    = string
  default = "coreflow-terraform-locks"
}

variable "cdn_bucket_names" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
