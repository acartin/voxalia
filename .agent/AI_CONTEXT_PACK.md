# AI Context Pack

- Generated UTC: `2026-08-06T01:57:10Z`
- Repo root: `/srv/voxalia`
- Git branch: `HETZNER-LOCAL-2026-Agosto-3`
- Git commit: `1742917`
- Policy: compact; read exact files only when the task needs them.

## Start Here

1. `.agent/AI_CONTEXT.md` for product and architecture direction.
2. `.agent/RULES.md` for safeguards.
3. `.agent/EXECUTION_MAP.md` for validation.
4. `.agent/ASTERISK_PROVISIONING_RULES.md` before changing Asterisk DB, menus, CRUDs, renderers or runtime behavior.
5. `.agent/WEB_UI_STANDARDS.md` only for `services/web/voxalia`.
6. `.agent/BRAIN_MAP.md` for routes and file entrypoints.

## Critical Safeguards

- No direct web-to-DB, web-to-Asterisk, web-to-Chatwoot or web-to-provider access.
- Backend/API must own tenant, auth, roles, menu and data scopes.
- No secrets in code, logs, docs or chat output.
- Provider-specific IDs and payloads are translated at adapters/connectors.
- Voice/WebRTC work must consider HTTPS/WSS, mic permissions, NAT, RTP, STUN/TURN and SIP credential exposure.
- Asterisk changes must close BD -> API/UI -> render -> Apply Config -> AMI reload -> runtime validation.
- Regenerate this pack only when structure/commit meaningfully changes.

## Compose Services

```text
postgres
redis
voxalia-asterisk-runtime
voxalia-asterisk-api
voxalia-web-api
voxalia-web
chatwoot
chatwoot-worker
freepbx-db
freepbx
```

## Operational Entry Points

```text
compose.yml
.env.example
README.md
services/web/voxalia
services/web-api
services/asterisk
services/asterisk-runtime
services/voice-runtime
channels/asterisk-adapter
channels/chatwoot-adapter
infra/asterisk
infra/freepbx
packages/auth
packages/domain
packages/events
packages/api-contracts
```

## Current Web App Contract

- Route: `services/web/voxalia`
- Stack: Next.js, TypeScript, Tailwind.
- Session cookie: `voxalia_session`.
- Placeholder auth: enabled when `VOXALIA_API_BASE_URL` is empty and `VOXALIA_PLACEHOLDER_AUTH` is not `false`.
- Default authenticated route: `/console/overview`.
- Compose service: `voxalia-web`.
- Default port: `8320`.

## Validation Shortcuts

```bash
docker compose config
docker build -t voxalia-web:dev services/web/voxalia
docker compose up -d --build voxalia-web
bash -n .agent/regenerar_contexto.sh
```
