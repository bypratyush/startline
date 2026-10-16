#!/usr/bin/env bash
# deploy.sh - install or upgrade StartLine with the images CI pushed to GHCR for one commit.
#   ./scripts/deploy.sh kind [sha]   local kind cluster (the live demo: commit -> pipeline -> this)
#   ./scripts/deploy.sh eks  [sha]   AWS EKS; the CI deploy job runs exactly this
# sha defaults to the first 7 characters of HEAD, the tag CI gives both images.
set -euo pipefail
cd "$(dirname "$0")/.."

target="${1:?usage: deploy.sh kind|eks [sha]}"
sha="${2:-$(git rev-parse HEAD | cut -c1-7)}"
owner="${GHCR_OWNER:-bypratyush}"
registry="ghcr.io/${owner}"

# The pipeline pushes the images a few minutes after the commit; wait for both.
for image in startline-backend startline-frontend; do
  until docker manifest inspect "${registry}/${image}:${sha}" >/dev/null 2>&1; do
    echo "waiting for ${registry}/${image}:${sha} (is the pipeline still running?)"
    sleep 15
  done
done
echo "images ${registry}/startline-{backend,frontend}:${sha} are in GHCR"

kubectl apply -f k8s/namespace.yaml

case "$target" in
  kind)
    values=helm/startline/values-dev.yaml
    extra=(--set image.pullPolicy=IfNotPresent)
    ;;
  eks)
    values=helm/startline/values-prod.yaml
    kubectl apply -f k8s/storageclass-gp3.yaml
    # the ingress controller; on EKS its Service becomes an AWS load balancer
    helm upgrade --install ingress-nginx ingress-nginx \
      --repo https://kubernetes.github.io/ingress-nginx \
      --namespace ingress-nginx --create-namespace --wait --timeout 10m
    # the database password is generated once, inside the cluster, never in Git
    kubectl -n startline get secret startline-db >/dev/null 2>&1 ||
      kubectl -n startline create secret generic startline-db \
        --from-literal=DB_PASSWORD="$(openssl rand -hex 16)"
    lb=""
    until [ -n "$lb" ]; do
      lb=$(kubectl -n ingress-nginx get svc ingress-nginx-controller \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
      [ -n "$lb" ] || { echo "waiting for the load balancer hostname"; sleep 10; }
    done
    extra=(--set ingress.host="$lb")
    ;;
  *)
    echo "unknown target: $target (kind or eks)" >&2
    exit 1
    ;;
esac

helm upgrade --install startline ./helm/startline \
  --namespace startline \
  -f "$values" \
  --set image.registry="$registry" \
  --set image.tag="$sha" \
  "${extra[@]}" \
  --wait --timeout 10m --atomic

kubectl -n startline get pods,svc,ingress
kubectl -n startline get deploy -o custom-columns=DEPLOYMENT:.metadata.name,IMAGE:.spec.template.spec.containers[0].image
if [ "$target" = eks ]; then
  echo "StartLine on EKS: http://${lb}"
fi
