#!/usr/bin/env bash
set -euo pipefail

bash /usr/local/bin/voxalia-ensure-freepbx-modules.sh &
ensure_pid="$!"

bash /usr/local/src/entrypoint.sh &
freepbx_pid="$!"

trap 'kill "$ensure_pid" "$freepbx_pid" 2>/dev/null || true' TERM INT

wait "$freepbx_pid"
