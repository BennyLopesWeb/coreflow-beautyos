bucket         = "coreflow-terraform-state"
key            = "ci-oidc/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "coreflow-terraform-locks"
encrypt        = true
