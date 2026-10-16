#!/usr/bin/env bash
# registration-rush.sh - load the backend until the HPA scales it out, then watch it scale back.
#   ./scripts/registration-rush.sh            (3 pods x 8 workers for 180 s)
#   IMAGE=ghcr.io/bypratyush/startline-backend:<sha> ./scripts/registration-rush.sh   (on EKS)
set -euo pipefail
cd "$(dirname "$0")/.."
NS=startline
IMAGE="${IMAGE:-startline-backend:local}"

kubectl -n "$NS" delete job startline-rush --ignore-not-found >/dev/null
kubectl -n "$NS" create configmap startline-loadgen --from-file=loadgen.py=scripts/loadgen.py \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null
sed "s#image: startline-backend:local#image: ${IMAGE}#" scripts/loadgen-job.yaml | kubectl apply -f - >/dev/null
echo "rush started at $(date +%T): watching the HPA every 15 s"
printf "%-8s  %-26s  %s\n" "TIME" "CPU (avg / target)" "REPLICAS"
for _ in $(seq 1 24); do
  line=$(kubectl -n "$NS" get hpa startline-backend --no-headers \
    -o custom-columns=T:.status.currentMetrics[0].resource.current.averageUtilization,R:.status.currentReplicas)
  set -- $line
  printf "%-8s  %-26s  %s\n" "$(date +%T)" "${1:-?}% / 60%" "${2:-?}"
  sleep 15
done
kubectl -n "$NS" logs job/startline-rush --tail=3 2>/dev/null || true
