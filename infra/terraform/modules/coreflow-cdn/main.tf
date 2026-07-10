variable "aws_region" {
  description = "Região AWS para S3 e CloudFront"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Nome do bucket S3 CDN"
  type        = string
}

variable "cdn_prefix" {
  description = "Prefixo S3 para arquivos CDN"
  type        = string
  default     = "cdn"
}

variable "cloudfront_aliases" {
  description = "CNAMEs CloudFront (hosts multi-tenant)"
  type        = list(string)
  default     = []
}

variable "cloudfront_price_class" {
  description = "PriceClass CloudFront"
  type        = string
  default     = "PriceClass_100"
}

variable "well_known_cache_seconds" {
  description = "TTL cache .well-known"
  type        = number
  default     = 86400
}

variable "tenant_behaviors" {
  description = "Cache behaviors por plugin vertical"
  type = list(object({
    plugin_id    = string
    path_pattern = string
    cdn_host     = string
    default_ttl  = number
    compress     = bool
  }))
  default = []
}

variable "tags" {
  description = "Tags AWS"
  type        = map(string)
  default     = {}
}

resource "aws_s3_bucket" "cdn" {
  bucket = var.bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_public_access_block" "cdn" {
  bucket                  = aws_s3_bucket.cdn.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "cdn" {
  name                              = "${var.bucket_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  comment             = "CoreFlow CDN multi-tenant"
  price_class         = var.cloudfront_price_class
  aliases             = var.cloudfront_aliases
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.cdn.bucket_regional_domain_name
    origin_id                = "coreflow-cdn-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.cdn.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "coreflow-cdn-s3"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = var.well_known_cache_seconds
    max_ttl     = var.well_known_cache_seconds
  }

  dynamic "ordered_cache_behavior" {
    for_each = var.tenant_behaviors
    content {
      path_pattern           = ordered_cache_behavior.value.path_pattern
      allowed_methods        = ["GET", "HEAD", "OPTIONS"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "coreflow-cdn-s3"
      viewer_protocol_policy = "redirect-to-https"
      compress               = ordered_cache_behavior.value.compress

      forwarded_values {
        query_string = false
        cookies {
          forward = "none"
        }
      }

      min_ttl     = 0
      default_ttl = ordered_cache_behavior.value.default_ttl
      max_ttl     = ordered_cache_behavior.value.default_ttl
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = length(var.cloudfront_aliases) == 0
  }

  tags = var.tags
}
