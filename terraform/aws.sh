#!/usr/bin/env bash
# aws.sh - the real AWS run. It costs money while it is up (EKS control plane,
# 2 x t3.medium, NAT gateway, load balancer): roughly USD 0.30 an hour.
#
#   ./terraform/aws.sh plan                 plan VPC + EKS + deploy role against your AWS account
#   ./terraform/aws.sh apply                apply that plan, then point kubectl at the new cluster
#   ./terraform/aws.sh down [-auto-approve] delete what Kubernetes created in AWS, then terraform destroy
#
# Uses your normal AWS credentials (aws configure, AWS_PROFILE or SSO). State lives
# in the "aws" workspace, apart from the LocalStack runs (run.sh, default workspace).
set -euo pipefail
cd "$(dirname "$0")"

vars=(-var use_localstack=false -var enable_eks=true)

terraform init -input=false >/dev/null
terraform workspace select -or-create aws >/dev/null
echo "workspace: $(terraform workspace show)   account: $(aws sts get-caller-identity --query Account --output text)"

case "${1:-}" in
  plan)
    terraform plan -input=false "${vars[@]}" -out aws.tfplan
    ;;
  apply)
    terraform apply -input=false aws.tfplan
    rm -f aws.tfplan
    eval "$(terraform output -raw configure_kubectl)"
    kubectl get nodes -o wide
    echo
    echo "To let the pipeline deploy, set the repository variable:"
    echo "  gh variable set AWS_DEPLOY_ROLE_ARN --body \"$(terraform output -raw github_deploy_role_arn)\""
    ;;
  down)
    shift
    # The ingress controller's load balancer and the database volume were made by
    # Kubernetes, not Terraform. Left behind they block the VPC delete and keep billing.
    if kubectl get namespace startline >/dev/null 2>&1; then
      kubectl delete namespace startline --wait --timeout 5m
    fi
    if helm status ingress-nginx -n ingress-nginx >/dev/null 2>&1; then
      helm uninstall ingress-nginx -n ingress-nginx --wait
      echo "waiting 90 s for AWS to release the load balancer's network interfaces"
      sleep 90
    fi
    terraform destroy -input=false "${vars[@]}" "$@"
    ;;
  *)
    echo "usage: aws.sh plan | apply | down [-auto-approve]" >&2
    exit 1
    ;;
esac
