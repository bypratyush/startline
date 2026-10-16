terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Local state for the LocalStack run. Against a real account the state moves
  # to S3 with native lock files:
  #
  # backend "s3" {
  #   bucket       = "startline-tfstate-24bcs10238"
  #   key          = "startline/terraform.tfstate"
  #   region       = "ap-south-1"
  #   use_lockfile = true
  # }
}
