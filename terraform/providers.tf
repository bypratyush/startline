# use_localstack = true  -> every API call goes to LocalStack (no AWS account needed)
# use_localstack = false -> real AWS, using the normal credential chain
provider "aws" {
  region = var.aws_region

  # Dummy keys for LocalStack only; on real AWS these stay null and the provider
  # reads env vars, ~/.aws/credentials or SSO instead.
  access_key = var.use_localstack ? "test" : null
  secret_key = var.use_localstack ? "test" : null

  skip_metadata_api_check     = var.use_localstack
  skip_credentials_validation = var.use_localstack
  skip_requesting_account_id  = var.use_localstack

  # Every service the configuration calls needs an override, otherwise that call
  # would quietly go to real AWS.
  dynamic "endpoints" {
    for_each = var.use_localstack ? [var.localstack_endpoint] : []
    content {
      ec2 = endpoints.value
      eks = endpoints.value
      iam = endpoints.value
      sts = endpoints.value
    }
  }

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "Terraform"
    }
  }
}
