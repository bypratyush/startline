#!/usr/bin/env bash
# run.sh - break StartLine three ways, investigate each like an on-call engineer, fix it.
#   ./troubleshooting/run.sh            all three faults
#   ./troubleshooting/run.sh image      only FAULT 1 (also: service, readiness)
set -uo pipefail
cd "$(dirname "$0")"
NS=startline
k() { echo "\$ kubectl $*"; kubectl "$@"; echo; }

fault_image() {
  echo "================ FAULT 1: broken image ================"
  kubectl apply -f broken-image.yaml
  sleep 20
  k -n $NS get pods -l app.kubernetes.io/name=startline-canary
  pod=$(kubectl -n $NS get pod -l app.kubernetes.io/name=startline-canary -o name | head -1)
  echo "\$ kubectl -n $NS describe $pod | sed -n '/Containers:/,/Ready:/p;/Events:/,\$p'"
  kubectl -n $NS describe "$pod" | sed -n '/Containers:/,/Ready:/p;/Events:/,$p'
  echo
  echo "\$ kubectl -n $NS get events --sort-by=.lastTimestamp --field-selector involvedObject.name=${pod#pod/} | tail -5"
  kubectl -n $NS get events --sort-by=.lastTimestamp --field-selector involvedObject.name="${pod#pod/}" | tail -5
  echo
  echo "# diagnosis: the tag startline-backend:v2.0-final does not exist in any registry the nodes can reach."
  echo "# fix: point the Deployment at an image that was actually built (CI tags = commit SHA)."
  k -n $NS set image deployment/startline-canary backend=startline-backend:local
  k -n $NS rollout status deployment/startline-canary --timeout=90s
  k -n $NS get pods -l app.kubernetes.io/name=startline-canary
  kubectl delete -f broken-image.yaml >/dev/null
}

fault_service() {
  echo "================ FAULT 2: Service with no endpoints ================"
  kubectl apply -f broken-service.yaml
  k -n $NS get svc startline-api
  k -n $NS get endpointslices -l kubernetes.io/service-name=startline-api
  echo "\$ kubectl -n $NS run probe --rm -i --restart=Never --image=startline-backend:local -- (GET http://startline-api:8000/health)"
  kubectl -n $NS run probe --rm -i --restart=Never --image=startline-backend:local --quiet \
    --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"probe","image":"startline-backend:local","command":["python","-c","import urllib.request as u\ntry:\n print(u.urlopen(\"http://startline-api:8000/health\", timeout=5).read().decode())\nexcept Exception as e:\n print(\"request failed:\", e)"],"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}}}]}}' \
    2>&1 | tail -2
  echo
  k -n $NS get svc startline-api -o jsonpath='{.spec.selector}{"\n"}'
  k -n $NS get pods -l app.kubernetes.io/component=backend --show-labels
  echo "# diagnosis: the selector asks for component=api; the pods are labelled component=backend."
  echo "# fix: make the selector match the pod labels."
  k -n $NS patch svc startline-api --type merge -p '{"spec":{"selector":{"app.kubernetes.io/component":"backend"}}}'
  sleep 3
  k -n $NS get endpointslices -l kubernetes.io/service-name=startline-api
  kubectl delete -f broken-service.yaml >/dev/null
}

fault_readiness() {
  echo "================ FAULT 3: Running but never Ready ================"
  kubectl apply -f broken-readiness.yaml
  sleep 30
  k -n $NS get pods -l app.kubernetes.io/name=startline-backend-misconfigured
  pod=$(kubectl -n $NS get pod -l app.kubernetes.io/name=startline-backend-misconfigured -o name | head -1)
  echo "\$ kubectl -n $NS describe $pod | grep -A6 Events: (readiness events)"
  kubectl -n $NS describe "$pod" | sed -n '/Events:/,$p' | grep -i -E "readiness|Events" | tail -4
  echo
  echo "\$ kubectl -n $NS exec $pod -- python -c (GET /health and /ready from inside the pod)"
  kubectl -n $NS exec "$pod" -- python -c "
import urllib.request, urllib.error
for path in ('/health', '/ready'):
    try:
        r = urllib.request.urlopen('http://127.0.0.1:8000' + path, timeout=3)
        print(path, r.status, r.read().decode())
    except urllib.error.HTTPError as e:
        print(path, e.code, e.read().decode())
"
  echo
  echo "# diagnosis: liveness (/health) passes, readiness (/ready) is 503 - the API cannot log in to Postgres."
  echo "# the DB_PASSWORD env var is a hard-coded literal instead of the Secret the real Deployment uses."
  echo "# fix: take the password from the Secret, exactly like the Helm chart does."
  k -n $NS patch deployment startline-backend-misconfigured --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/env/0","value":{"name":"DB_PASSWORD","valueFrom":{"secretKeyRef":{"name":"startline-db","key":"DB_PASSWORD"}}}}]'
  k -n $NS rollout status deployment/startline-backend-misconfigured --timeout=120s
  k -n $NS get pods -l app.kubernetes.io/name=startline-backend-misconfigured
  kubectl delete -f broken-readiness.yaml >/dev/null
}

case "${1:-all}" in
  image) fault_image ;;
  service) fault_service ;;
  readiness) fault_readiness ;;
  all) fault_image; fault_service; fault_readiness ;;
  *) echo "usage: $0 [image|service|readiness|all]"; exit 1 ;;
esac
