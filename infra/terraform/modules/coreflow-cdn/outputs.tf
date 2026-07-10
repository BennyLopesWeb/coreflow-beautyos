output "bucket_name" {
  description = "Nome do bucket S3 CDN"
  value       = aws_s3_bucket.cdn.bucket
}

output "bucket_arn" {
  description = "ARN do bucket S3"
  value       = aws_s3_bucket.cdn.arn
}

output "cloudfront_distribution_id" {
  description = "ID da distribuição CloudFront"
  value       = aws_cloudfront_distribution.cdn.id
}

output "cloudfront_domain_name" {
  description = "Domain name CloudFront (*.cloudfront.net)"
  value       = aws_cloudfront_distribution.cdn.domain_name
}

output "cloudfront_aliases" {
  description = "Aliases configurados"
  value       = var.cloudfront_aliases
}
