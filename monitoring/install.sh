#!/usr/bin/env bash
# install.sh            install or upgrade kube-prometheus-stack + the StartLine dashboard
# install.sh dashboard  only (re)apply the Grafana dashboard ConfigMap
# install.sh open       port-forward Prometheus (9090) and Grafana (3001), if the Ingress URLs are not used
#
# With the chart installed, both are also on the Ingress: http://grafana.localhost, http://prometheus.localhost
set -euo pipefail
cd "$(dirname "$0")"

dashboard() {
  kubectl apply -f grafana-dashboard-configmap.yaml
}

case "${1:-install}" in
  install)
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
    helm repo update prometheus-community >/dev/null
    helm upgrade --install monitoring prometheus-community/kube-prometheus-stack --version 92.1.0 \
      -n monitoring --create-namespace -f kube-prometheus-stack-values.yaml --wait --timeout 10m
    dashboard
    ;;
  dashboard)
    dashboard
    ;;
  open)
    echo "Prometheus http://localhost:9090   Grafana http://localhost:3001 (admin / startline-grafana)"
    kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 &
    kubectl -n monitoring port-forward svc/monitoring-grafana 3001:80
    ;;
  *)
    echo "usage: $0 [install|dashboard|open]"; exit 1 ;;
esac
