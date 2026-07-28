output "role_arn" {
  description = "ARN da role — configurar como secret GitHub AWS_ROLE_ARN."
  value       = aws_iam_role.github_actions.arn
}

output "role_name" {
  description = "Nome da IAM Role."
  value       = aws_iam_role.github_actions.name
}

output "oidc_provider_arn" {
  description = "ARN do OIDC provider GitHub Actions."
  value       = local.oidc_provider_arn
}
