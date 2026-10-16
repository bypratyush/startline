#!/bin/sh
# 1. run database migrations (Postgres may still be starting: retry)
# 2. load or refresh the event catalogue (idempotent upsert)
# 3. start the API
# Steps 1 and 2 take a Postgres advisory lock, so several replicas starting at
# once take turns instead of racing.
set -e

retry() {
  n=0
  until "$@"; do
    n=$((n + 1))
    if [ "$n" -ge 20 ]; then
      echo "giving up after $n attempts: $*" >&2
      exit 1
    fi
    echo "attempt $n failed (database not ready?), retrying in 3s: $*" >&2
    sleep 3
  done
}

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  retry alembic upgrade head
fi

if [ "${SEED_ON_START:-true}" = "true" ]; then
  retry python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WEB_WORKERS:-1}" --no-access-log --proxy-headers
