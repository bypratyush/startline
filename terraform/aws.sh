#!/usr/bin/env bash
# aws.sh - the real AWS run. It costs money while it is up (EKS control plane,
# 2 x c7i-flex.large, NAT gateway, load balancer): roughly USD 0.30 an hour.
#
#   ./terraform/aws.sh plan                 plan VPC + EKS + deploy role against your AWS account
#   ./terraform/aws.sh apply                apply that plan, then add the cluster to kubectl as "startline-eks"
#   ./terraform/aws.sh down [-auto-approve] delete what Kubernetes created in AWS, then terraform destroy
#
# Uses your normal AWS credentials (aws login, aws configure, AWS_PROFILE or SSO).
# State lives in the "aws" workspace, apart from the LocalStack runs (run.sh).
set -euo pipefail
cd "$(dirname "$0")"

export AWS_REGION="${AWS_REGION:-ap-south-1}"
vars=(-var use_localstack=false -var enable_eks=true -var aws_region="$AWS_REGION")
ctx=startline-eks # kubectl context name; never the current context, which may be kind

terraform init -input=false >/dev/null
terraform workspace select -or-create aws >/dev/null
echo "workspace: $(terraform workspace show)   account: $(aws sts get-caller-identity --query Account --output text)   region: $AWS_REGION"

# Add the cluster to kubeconfig as "$ctx" without leaving it as the current context.
add_context() {
  local prev
  prev=$(kubectl config current-context 2>/dev/null || true)
  aws eks update-kubeconfig --name "$1" --alias "$ctx" >/dev/null
  if [ -n "$prev" ]; then kubectl config use-context "$prev" >/dev/null; fi
}

case "${1:-}" in
  plan)
    terraform plan -input=false "${vars[@]}" -out aws.tfplan
    ;;
  apply)
    terraform apply -input=false aws.tfplan
    rm -f aws.tfplan
    add_context "$(terraform output -raw cluster_name)"
    kubectl --context "$ctx" get nodes -o wide
    echo
    echo "To let the pipeline deploy, set the repository variable:"
    echo "  gh variable set AWS_DEPLOY_ROLE_ARN --body \"$(terraform output -raw github_deploy_role_arn)\""
    ;;
  down)
    shift
    cluster=$(terraform output -raw cluster_name 2>/dev/null || true)
    if [ -n "$cluster" ] && aws eks describe-cluster --name "$cluster" >/dev/null 2>&1; then
      add_context "$cluster"
      # The ingress controller's load balancer and the database volume were made by
      # Kubernetes, not Terraform. Left behind they block the VPC delete and keep billing.
      if kubectl --context "$ctx" get namespace startline >/dev/null 2>&1; then
        kubectl --context "$ctx" delete namespace startline --wait --timeout 5m
      fi
      # gp3 volumes are Retain (a deleted claim must not take the database with it),
      # so the EBS volumes outlive the namespace: delete them explicitly.
      for pv in $(kubectl --context "$ctx" get pv -o jsonpath='{range .items[?(@.spec.storageClassName=="gp3")]}{.metadata.name}{" "}{end}'); do
        vol=$(kubectl --context "$ctx" get pv "$pv" -o jsonpath='{.spec.csi.volumeHandle}')
        kubectl --context "$ctx" delete pv "$pv" --wait=false
        aws ec2 wait volume-available --volume-ids "$vol"
        aws ec2 delete-volume --volume-id "$vol" && echo "deleted EBS volume $vol"
      done
      if helm --kube-context "$ctx" status ingress-nginx -n ingress-nginx >/dev/null 2>&1; then
        helm --kube-context "$ctx" uninstall ingress-nginx -n ingress-nginx --wait
        echo "waiting 90 s for AWS to release the load balancer's network interfaces"
        sleep 90
      fi
    fi
    vpc=$(terraform output -raw vpc_id 2>/dev/null || true)
    # 1. the cluster first (node group, add-ons, access entries go with it)
    terraform destroy -input=false "${vars[@]}" -target=aws_eks_cluster.main "$@"
    # 2. what EKS leaves in the VPC: network interfaces the VPC CNI opened on the nodes,
    #    and the cluster security group when one of those was still using it. Either
    #    blocks the subnet and VPC delete.
    if [ -n "$vpc" ]; then
      for eni in $(aws ec2 describe-network-interfaces --filters "Name=vpc-id,Values=$vpc" "Name=status,Values=available" \
        --query 'NetworkInterfaces[?starts_with(Description, `aws-K8S-`)].NetworkInterfaceId' --output text); do
        aws ec2 delete-network-interface --network-interface-id "$eni" && echo "deleted leftover network interface $eni"
      done
      for sg in $(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$vpc" "Name=group-name,Values=eks-cluster-sg-*" \
        --query 'SecurityGroups[].GroupId' --output text); do
        aws ec2 delete-security-group --group-id "$sg" >/dev/null && echo "deleted leftover security group $sg"
      done
    fi
    # 3. everything else
    terraform destroy -input=false "${vars[@]}" "$@"
    # EKS writes control-plane logs to a log group Terraform does not create
    if [ -n "$cluster" ]; then
      aws logs delete-log-group --log-group-name "/aws/eks/$cluster/cluster" 2>/dev/null && echo "deleted log group /aws/eks/$cluster/cluster" || true
    fi
    kubectl config delete-context "$ctx" >/dev/null 2>&1 || true
    ;;
  *)
    echo "usage: aws.sh plan | apply | down [-auto-approve]" >&2
    exit 1
    ;;
esac
