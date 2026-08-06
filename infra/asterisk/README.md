# Asterisk Infra

Asterisk configuration, dialplans, and voice infrastructure templates.

## Voxalia-managed config

Voxalia treats PostgreSQL as the source of truth and Asterisk as the runtime.
`services/asterisk` renders the desired state and, on `Apply Config`, writes
only Voxalia-owned files:

```text
pjsip_voxalia.conf
extensions_voxalia.conf
queues_voxalia.conf
voxalia-routing.preview
voxalia-recording.preview
```

These files are written atomically under
`VOXALIA_ASTERISK_API_RENDER_OUTPUT_DIR`. In local compose that path is backed
by the `voxalia-asterisk-rendered` volume and mounted into
`voxalia-asterisk-runtime` at `/etc/asterisk/voxalia`.

The local production-shaped runtime is `voxalia-asterisk-runtime`, a direct
Asterisk container. It includes these generated files from its main config:

```text
; pjsip.conf
#include voxalia/pjsip_voxalia.conf

; extensions.conf
#include voxalia/extensions_voxalia.conf

; queues.conf
#include voxalia/queues_voxalia.conf
```

The main Asterisk files, transports, certificates, RTP/NAT settings and other
non-Voxalia runtime configuration remain outside this generated scope. FreePBX
is kept only as a lab/reference container and does not receive Voxalia apply
config writes.
