bucket         = "coreflow-terraform-state"
key            = "cdn/staging/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "coreflow-terraform-locks"
encrypt        = true
