# AI Context Pack

- Generated UTC: `2026-07-24T18:37:23Z`
- Repo root: `/srv/voxalia`
- Git branch: `HETZNER-LOCAL-2026-Julio-23`
- Git commit: `0cf0080`
- Policy: compact; read exact files only when the task needs them.

## Start Here

1. `.agent/AI_CONTEXT.md` for product and architecture direction.
2. `.agent/RULES.md` for safeguards.
3. `.agent/EXECUTION_MAP.md` for validation.
4. `.agent/WEB_UI_STANDARDS.md` only for `services/web/voxalia`.
5. `.agent/BRAIN_MAP.md` for routes and file entrypoints.

## Critical Safeguards

- No direct web-to-DB, web-to-Asterisk, web-to-Chatwoot or web-to-provider access.
- Backend/API must own tenant, auth, roles, menu and data scopes.
- No secrets in code, logs, docs or chat output.
- Provider-specific IDs and payloads are translated at adapters/connectors.
- Voice/WebRTC work must consider HTTPS/WSS, mic permissions, NAT, RTP, STUN/TURN and SIP credential exposure.
- Regenerate this pack only when structure/commit meaningfully changes.

## Compose Services

```text
freepbx-db
freepbx
postgres
redis
voxalia-web
chatwoot
chatwoot-worker
```

## Operational Entry Points

```text
compose.yml
.env.example
README.md
services/web/voxalia
services/web-api
services/voice-runtime
channels/asterisk-adapter
channels/chatwoot-adapter
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
