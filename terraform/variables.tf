# ---- where ------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region for every resource (Mumbai)."
  type        = string
  default     = "ap-south-1"
}

variable "use_localstack" {
  description = "true = LocalStack on localhost, false = real AWS."
  type        = bool
  default     = true
}

variable "localstack_endpoint" {
  description = "LocalStack edge URL (ignored when use_localstack = false)."
  type        = string
  default     = "http://localhost:4568"
}

# ---- naming -----------------------------------------------------------------

variable "project_name" {
  description = "Prefix for resource names and the Project tag."
  type        = string
  default     = "startline"
}

variable "environment" {
  description = "Environment tag."
  type        = string
  default     = "prod"
}

variable "owner" {
  description = "Owner tag."
  type        = string
  default     = "Pratyush Mohanty"
}

# ---- network ----------------------------------------------------------------

variable "vpc_cidr" {
  description = "Address space for the whole VPC."
  type        = string
  default     = "10.40.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block, for example 10.40.0.0/16."
  }
}

variable "availability_zones" {
  description = "At least two AZs: EKS refuses a cluster whose subnets are all in one AZ."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "EKS needs subnets in at least two availability zones."
  }
}

variable "single_nat_gateway" {
  description = "One shared NAT gateway (cheaper) instead of one per AZ (survives an AZ outage)."
  type        = bool
  default     = true
}

# ---- EKS --------------------------------------------------------------------

variable "enable_eks" {
  description = "Create the NAT gateway, EKS cluster, node group and add-ons. LocalStack Community has no EKS API, so the local run uses false."
  type        = bool
  default     = false
}

variable "eks_version" {
  description = "Kubernetes version of the control plane."
  type        = string
  default     = "1.35"
}

variable "node_instance_types" {
  description = "Instance types for the managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_scaling" {
  description = "Managed node group size. The HPA scales pods; this is the room it has."
  type = object({
    min     = number
    desired = number
    max     = number
  })
  default = { min = 2, desired = 2, max = 4 }

  validation {
    condition     = var.node_scaling.min <= var.node_scaling.desired && var.node_scaling.desired <= var.node_scaling.max
    error_message = "node_scaling must satisfy min <= desired <= max."
  }
}

variable "api_allowed_cidrs" {
  description = "CIDRs allowed to reach the public EKS API endpoint. Narrow this to your office or VPN."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
