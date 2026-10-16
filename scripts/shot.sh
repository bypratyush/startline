#!/usr/bin/env bash
# shot.sh - capture a real terminal screenshot of a command and its output (termshot).
#   ./scripts/shot.sh screenshots/pods.png kubectl get pods -n startline
#   WIDTH=170 ./scripts/shot.sh screenshots/x.png <command...>
set -euo pipefail
OUT="$1"; shift
WIDTH="${WIDTH:-150}"
mkdir -p "$(dirname "$OUT")"
# termshot needs a TTY to size its pty; script(1) provides one from a non-interactive shell
script -q /dev/null termshot --show-cmd --columns "$WIDTH" --filename "$OUT" -- "$@" >/dev/null 2>&1 || true
[ -f "$OUT" ] && echo "  $(basename "$OUT")" || { echo "  FAILED: $OUT" >&2; exit 1; }
