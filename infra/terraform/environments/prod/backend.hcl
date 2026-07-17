bucket         = "coreflow-terraform-state"
key            = "cdn/prod/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "coreflow-terraform-locks"
encrypt        = true
