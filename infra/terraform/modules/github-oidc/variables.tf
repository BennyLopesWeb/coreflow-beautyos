variable "github_org" {
  description = "Organização ou usuário dono do repositório GitHub."
  type        = string
}

variable "github_repo" {
  description = "Nome do repositório GitHub (sem org)."
  type        = string
}

variable "github_ref_filter" {
  description = "Filtro do claim sub (ex. * ou environment:production)."
  type        = string
  default     = "*"
}

variable "role_name" {
  description = "Nome da IAM Role assumida pelos workflows."
  type        = string
  default     = "coreflow-github-actions"
}

variable "create_oidc_provider" {
  description = "Se true, cria o OIDC provider; se false, reutiliza o existente na conta."
  type        = bool
  default     = true
}

variable "state_bucket" {
  description = "Bucket S3 do remote state Terraform."
  type        = string
  default     = "coreflow-terraform-state"
}

variable "lock_table" {
  description = "Tabela DynamoDB de locks Terraform."
  type        = string
  default     = "coreflow-terraform-locks"
}

variable "cdn_bucket_names" {
  description = "Buckets S3 CDN que a role pode gerenciar/sync."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags AWS aplicadas à role/provider."
  type        = map(string)
  default     = {}
}
