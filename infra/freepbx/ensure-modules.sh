#!/usr/bin/env bash
set -euo pipefail

modules=(
  ringgroups
  queues
)

log() {
  printf '[voxalia-freepbx-modules] %s\n' "$*"
}

wait_for_fwconsole() {
  for attempt in $(seq 1 60); do
    if fwconsole ma list >/tmp/voxalia-fwconsole-ma-list.out 2>/tmp/voxalia-fwconsole-ma-list.err; then
      return 0
    fi

    log "waiting for fwconsole (${attempt}/60)"
    sleep 5
  done

  log "fwconsole did not become ready"
  cat /tmp/voxalia-fwconsole-ma-list.err >&2 || true
  return 1
}

wait_for_fwconsole

changed=0
for module in "${modules[@]}"; do
  if fwconsole ma list | awk -F'|' -v module="$module" '$2 ~ module && $4 ~ /Enabled/ { found=1 } END { exit found ? 0 : 1 }'; then
    log "$module already enabled"
    continue
  fi

  log "installing $module"
  fwconsole ma downloadinstall "$module"
  changed=1
done

if [ "$changed" -eq 1 ]; then
  log "reloading FreePBX"
  fwconsole reload
fi

log "module check complete"
