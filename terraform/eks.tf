# EKS control plane, a managed node group in the private subnets, and the
# add-ons StartLine relies on. Everything here sits behind enable_eks.

resource "aws_eks_cluster" "main" {
  count    = var.enable_eks ? 1 : 0
  name     = local.cluster_name
  version  = var.eks_version
  role_arn = aws_iam_role.cluster.arn

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    subnet_ids              = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.api_allowed_cidrs
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator"]

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

# IMDSv2 only, and our node security group next to the cluster one.
resource "aws_launch_template" "nodes" {
  count                  = var.enable_eks ? 1 : 0
  name_prefix            = "${var.project_name}-nodes-"
  vpc_security_group_ids = [aws_security_group.nodes.id, aws_eks_cluster.main[0].vpc_config[0].cluster_security_group_id]

  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${var.project_name}-node" }
  }
}

resource "aws_eks_node_group" "main" {
  count           = var.enable_eks ? 1 : 0
  cluster_name    = aws_eks_cluster.main[0].name
  node_group_name = "${var.project_name}-nodes"
  node_role_arn   = aws_iam_role.nodes.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.node_instance_types
  capacity_type   = "ON_DEMAND"

  scaling_config {
    min_size     = var.node_scaling.min
    desired_size = var.node_scaling.desired
    max_size     = var.node_scaling.max
  }

  update_config {
    max_unavailable = 1
  }

  launch_template {
    id      = aws_launch_template.nodes[0].id
    version = aws_launch_template.nodes[0].latest_version
  }

  labels = { workload = "startline" }

  depends_on = [aws_iam_role_policy_attachment.nodes, aws_route.private_nat]
}

# Managed add-ons: networking, DNS, Pod Identity (for the EBS driver),
# the EBS CSI driver (Postgres PVC) and metrics-server (needed by the HPA).
locals {
  addons = var.enable_eks ? toset([
    "vpc-cni", "coredns", "kube-proxy", "eks-pod-identity-agent", "aws-ebs-csi-driver", "metrics-server",
  ]) : toset([])
}

resource "aws_eks_addon" "this" {
  for_each                    = local.addons
  cluster_name                = aws_eks_cluster.main[0].name
  addon_name                  = each.key
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  dynamic "pod_identity_association" {
    for_each = each.key == "aws-ebs-csi-driver" ? [1] : []
    content {
      role_arn        = aws_iam_role.ebs_csi.arn
      service_account = "ebs-csi-controller-sa"
    }
  }

  depends_on = [aws_eks_node_group.main]
}
