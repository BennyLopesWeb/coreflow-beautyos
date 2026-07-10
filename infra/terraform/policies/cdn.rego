package coreflow.cdn

import rego.v1

# Políticas CDN Terraform — CoreFlow Platform (CF-23)
# Input: {"environment": "prod", "tfvars": {...}}

deny contains msg if {
	input.environment == "prod"
	input.tfvars.cloudfront_price_class != "PriceClass_All"
	msg := "prod deve usar cloudfront_price_class=PriceClass_All"
}

deny contains msg if {
	input.environment == "prod"
	not endswith(input.tfvars.bucket_name, "-prod")
	msg := "prod bucket_name deve terminar com -prod"
}

deny contains msg if {
	input.environment == "staging"
	not endswith(input.tfvars.bucket_name, "-staging")
	msg := "staging bucket_name deve terminar com -staging"
}

deny contains msg if {
	input.environment == "dev"
	not endswith(input.tfvars.bucket_name, "-dev")
	msg := "dev bucket_name deve terminar com -dev"
}

deny contains msg if {
	input.tfvars.tags.Environment != input.environment
	msg := "tags.Environment deve corresponder ao ambiente"
}

deny contains msg if {
	count(input.tfvars.tenant_behaviors) < 1
	msg := "tenant_behaviors não pode ser vazio"
}
