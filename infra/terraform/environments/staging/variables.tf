variable "aws_region" { type = string }
variable "bucket_name" { type = string }
variable "cdn_prefix" { type = string }
variable "cloudfront_aliases" { type = list(string) }
variable "cloudfront_price_class" { type = string }
variable "well_known_cache_seconds" { type = number }
variable "tenant_behaviors" {
  type = list(object({
    plugin_id    = string
    path_pattern = string
    cdn_host     = string
    default_ttl  = number
    compress     = bool
  }))
}
variable "tags" { type = map(string) }

output "cloudfront_distribution_id" {
  value = module.coreflow_cdn.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  value = module.coreflow_cdn.cloudfront_domain_name
}
