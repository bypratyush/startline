output "vpc_id" {
  description = "VPC id."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnets (load balancers, NAT)."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnets (worker nodes)."
  value       = aws_subnet.private[*].id
}

output "node_security_group_id" {
  description = "Extra security group attached to the worker nodes."
  value       = aws_security_group.nodes.id
}

output "cluster_name" {
  description = "EKS cluster name (null until enable_eks = true)."
  value       = try(aws_eks_cluster.main[0].name, null)
}

output "cluster_endpoint" {
  description = "EKS API endpoint."
  value       = try(aws_eks_cluster.main[0].endpoint, null)
}

output "configure_kubectl" {
  description = "Run this after apply to point kubectl at the new cluster."
  value       = var.enable_eks ? "aws eks update-kubeconfig --region ${var.aws_region} --name ${local.cluster_name}" : "enable_eks = false: no cluster created"
}

output "nat_gateway_public_ips" {
  description = "Egress IPs of the private subnets (allow-list these at third parties)."
  value       = aws_eip.nat[*].public_ip
}

output "github_deploy_role_arn" {
  description = "Set this as the AWS_DEPLOY_ROLE_ARN repository variable to switch on the CI deploy job."
  value       = aws_iam_role.github_deploy.arn
}
