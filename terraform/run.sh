#!/usr/bin/env bash
# run.sh - prove the Terraform end to end without an AWS account.
#
#   1. start LocalStack 4.14.0 (last Community build that runs without a token)
#      in its own container on localhost:4568
#   2. terraform plan with enable_eks = true   -> shows the full EKS design (39 resources)
#   3. terraform apply with enable_eks = false -> VPC, subnets, routes, SG, IAM really created
#   4. inspect them with the AWS CLI, then terraform destroy and remove LocalStack
#
# Against real AWS: cp terraform.tfvars.example terraform.tfvars, then
#   terraform init && terraform plan && terraform apply
set -euo pipefail
cd "$(dirname "$0")"

NAME=localstack-startline
PORT=4568
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=ap-south-1
AWS="aws --endpoint-url http://localhost:${PORT} --output table"

echo "== LocalStack"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:4566" localstack/localstack:4.14.0 >/dev/null
for _ in $(seq 1 60); do
  curl -sf "http://localhost:${PORT}/_localstack/health" | grep -q '"ec2": "\(available\|running\)"' && break
  sleep 2
done
echo "localstack up on :${PORT}"

terraform init -input=false >/dev/null
terraform workspace select default >/dev/null   # aws.sh keeps the real-AWS state in its own workspace
terraform fmt -check -recursive
terraform validate

echo "== plan with the EKS cluster (design check, not applied: LocalStack Community has no EKS)"
terraform plan -input=false -no-color -var enable_eks=true -out eks.tfplan | grep "^Plan:"
terraform show -json eks.tfplan | python3 -c "
import json, sys, collections
plan = json.load(sys.stdin)
kinds = collections.Counter(r['type'] for r in plan['resource_changes'] if 'create' in r['change']['actions'])
for k, n in sorted(kinds.items()):
    print(f'  {n:2d} x {k}')
"

echo "== apply the network and IAM (enable_eks = false)"
terraform apply -input=false -no-color -auto-approve -var enable_eks=false | grep "^Apply complete"
terraform output

echo "== what exists now (AWS CLI against LocalStack)"
VPC=$(terraform output -raw vpc_id)
$AWS ec2 describe-vpcs --vpc-ids "$VPC" --query 'Vpcs[].{Vpc:VpcId,Cidr:CidrBlock}'
$AWS ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" \
  --query 'sort_by(Subnets,&CidrBlock)[].{Cidr:CidrBlock,AZ:AvailabilityZone,PublicIp:MapPublicIpOnLaunch,Name:Tags[?Key==`Name`]|[0].Value}'
$AWS ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC" \
  --query 'RouteTables[].{Name:Tags[?Key==`Name`]|[0].Value,Routes:length(Routes),Subnets:length(Associations)}'
$AWS iam list-roles --query 'Roles[?starts_with(RoleName,`startline`)].{Role:RoleName}'

echo "== destroy"
terraform destroy -input=false -no-color -auto-approve -var enable_eks=false | grep "^Destroy complete"
rm -f eks.tfplan
docker rm -f "$NAME" >/dev/null
echo "localstack removed"
