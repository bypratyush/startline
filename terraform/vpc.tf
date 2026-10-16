# VPC with a public and a private subnet in each AZ.
#   public  : load balancer for the Ingress, NAT gateway
#   private : EKS worker nodes and the Postgres volume; no public IPs
locals {
  azs             = var.availability_zones
  public_subnets  = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i + 1)]  # 10.40.1.0/24, 10.40.2.0/24
  private_subnets = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i + 11)] # 10.40.11.0/24, 10.40.12.0/24
  cluster_name    = "${var.project_name}-eks"
  nat_count       = var.enable_eks ? (var.single_nat_gateway ? 1 : length(local.azs)) : 0
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true # EKS nodes need DNS hostnames to register

  tags = { Name = "${var.project_name}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-igw" }
}

resource "aws_subnet" "public" {
  count                   = length(local.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnets[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${local.azs[count.index]}"
    # the AWS load balancer controller / in-tree LB put internet-facing LBs here
    "kubernetes.io/role/elb"                      = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }
}

resource "aws_subnet" "private" {
  count             = length(local.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnets[count.index]
  availability_zone = local.azs[count.index]

  tags = {
    Name                                          = "${var.project_name}-private-${local.azs[count.index]}"
    "kubernetes.io/role/internal-elb"             = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = length(local.azs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# NAT: private nodes reach GHCR, Docker Hub and the EKS API without a public IP.
# Only created with the cluster, because a NAT gateway is billed per hour.
resource "aws_eip" "nat" {
  count  = local.nat_count
  domain = "vpc"
  tags   = { Name = "${var.project_name}-nat-eip-${count.index}" }
}

resource "aws_nat_gateway" "main" {
  count         = local.nat_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${var.project_name}-nat-${count.index}" }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private" {
  count  = length(local.azs)
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-private-rt-${local.azs[count.index]}" }
}

resource "aws_route" "private_nat" {
  count                  = var.enable_eks ? length(local.azs) : 0
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[var.single_nat_gateway ? 0 : count.index].id
}

resource "aws_route_table_association" "private" {
  count          = length(local.azs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Extra security group for the worker nodes. EKS also attaches its own cluster
# security group; this one documents and controls node-to-node traffic.
resource "aws_security_group" "nodes" {
  name        = "${var.project_name}-eks-nodes"
  description = "EKS worker nodes for StartLine"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.project_name}-eks-nodes" }
}

resource "aws_vpc_security_group_ingress_rule" "nodes_self" {
  security_group_id            = aws_security_group.nodes.id
  referenced_security_group_id = aws_security_group.nodes.id
  ip_protocol                  = "-1"
  description                  = "Pod and node traffic between workers"
}

resource "aws_vpc_security_group_ingress_rule" "nodes_from_vpc_https" {
  security_group_id = aws_security_group.nodes.id
  cidr_ipv4         = var.vpc_cidr
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "Control plane to kubelet and webhooks"
}

resource "aws_vpc_security_group_ingress_rule" "nodes_from_vpc_kubelet" {
  security_group_id = aws_security_group.nodes.id
  cidr_ipv4         = var.vpc_cidr
  ip_protocol       = "tcp"
  from_port         = 10250
  to_port           = 10250
  description       = "Control plane to kubelet (logs, exec, metrics-server)"
}

resource "aws_vpc_security_group_egress_rule" "nodes_all" {
  security_group_id = aws_security_group.nodes.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Pull images, reach the EKS API, DNS"
}
