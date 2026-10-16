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

case "${1:-}" in
  plan)
    terraform plan -input=false "${vars[@]}" -out aws.tfplan
    ;;
  apply)
    terraform apply -input=false aws.tfplan
    rm -f aws.tfplan
    aws eks update-kubeconfig --name "$(terraform output -raw cluster_name)" --alias "$ctx"
    kubectl --context "$ctx" get nodes -o wide
    echo
    echo "To let the pipeline deploy, set the repository variable:"
    echo "  gh variable set AWS_DEPLOY_ROLE_ARN --body \"$(terraform output -raw github_deploy_role_arn)\""
    ;;
  down)
    shift
    cluster=$(terraform output -raw cluster_name 2>/dev/null || true)
    if [ -n "$cluster" ] && aws eks describe-cluster --name "$cluster" >/dev/null 2>&1; then
      aws eks update-kubeconfig --name "$cluster" --alias "$ctx" >/dev/null
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
    terraform destroy -input=false "${vars[@]}" "$@"
    kubectl config delete-context "$ctx" >/dev/null 2>&1 || true
    ;;
  *)
    echo "usage: aws.sh plan | apply | down [-auto-approve]" >&2
    exit 1
    ;;
esac
