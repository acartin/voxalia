# BRAIN_MAP

- Generated UTC: `2026-07-24T18:37:23Z`
- Repo root: `/srv/voxalia`
- Git branch: `HETZNER-LOCAL-2026-Julio-23`
- Git commit: `0cf0080`
- Policy: high-signal only; Voxalia safeguards, security and context economy.

## 1. Mapa De Intenciones

| Ruta | Responsabilidad | Importancia |
|---|---|---:|
| `compose.yml` | Entrada operativa local: Postgres, Redis, Chatwoot, FreePBX/Asterisk y Voxalia Web. | 5 |
| `.agent/AI_CONTEXT.md` | Contexto rector de negocio, dominio y arquitectura. | 5 |
| `services/web/voxalia` | Consola web Next.js y shell de portal. | 5 |
| `services/web-api` | API/BFF autoritativo para auth, tenant, menu y datos consumidos por la web. | 5 |
| `services/voice-runtime` | Futuro runtime de coordinacion de voz alrededor de Asterisk. | 5 |
| `channels` | Adaptadores de canales externos a contratos internos. | 4 |
| `connectors` | Integraciones externas PMS/CRM/pagos/correo. | 4 |
| `packages` | Contratos, dominio, auth, eventos, config y observabilidad compartida. | 4 |
| `infra/freepbx` | Soporte de FreePBX/Asterisk local. | 4 |
| `verticals` | Politicas, prompts, schemas y workflows por vertical. | 3 |

## 2. Limites Criticos

- Apps web no hablan directo con DB, Asterisk, Chatwoot, FreePBX ni proveedores.
- Backend resuelve tenant, rol, permisos, menu y scopes de datos.
- Proveedores viven detras de `channels` o `connectors`.
- Dominio compartido no contiene condiciones por cliente o vertical.
- Cambios de compose/env deben actualizar `.env.example`, README y contexto operativo si aplica.

## 3. Servicios Compose

```text
freepbx-db
freepbx
postgres
redis
voxalia-web
chatwoot
chatwoot-worker
```

## 4. Topologia Compacta

```text
apps
apps/admin-web
apps/client-portal
apps/operator-console
channels
channels/asterisk-adapter
channels/chatwoot-adapter
channels/meta-adapter
channels/webchat-adapter
connectors
connectors/cloudbeds
connectors/crm
connectors/email
connectors/generic-pms
connectors/payments
docs
docs/adr
docs/architecture
docs/operations
infra
infra/asterisk
infra/backup
infra/compose
infra/deploy
infra/freepbx
infra/reverse-proxy
infra/wireguard
packages
packages/api-contracts
packages/auth
packages/config
packages/domain
packages/events
packages/observability
products
products/agent-assist
products/automated-chat
products/call-intelligence
products/managed-reception
products/multichannel-inbox
products/sales-followup
services
services/web-api
services/web-api/db
services/voice-runtime
services/web
services/web/voxalia
services/worker
verticals
verticals/_template
verticals/hospitality
verticals/hospitality/policies
verticals/hospitality/prompts
verticals/hospitality/schemas
verticals/hospitality/tool-bindings
verticals/hospitality/workflows
```

## 5. Archivos De Entrada

```text
README.md
.env.example
compose.yml
.agent/AI_CONTEXT.md
.agent/RULES.md
.agent/EXECUTION_MAP.md
.agent/WEB_UI_STANDARDS.md
apps/README.md
apps/admin-web/README.md
apps/client-portal/README.md
apps/operator-console/README.md
channels/README.md
channels/asterisk-adapter/README.md
channels/chatwoot-adapter/README.md
channels/meta-adapter/README.md
channels/webchat-adapter/README.md
connectors/README.md
connectors/cloudbeds/README.md
connectors/crm/README.md
connectors/email/README.md
connectors/generic-pms/README.md
connectors/payments/README.md
docs/README.md
docs/adr/0001-managed-reception-hospitality-domain.md
docs/adr/README.md
docs/architecture/README.md
docs/operations/README.md
infra/README.md
infra/asterisk/README.md
infra/backup/README.md
infra/compose/README.md
infra/deploy/README.md
infra/freepbx/README.md
infra/freepbx/ensure-modules.sh
infra/freepbx/entrypoint-with-modules.sh
infra/freepbx/init.sql
infra/freepbx/my.cnf
infra/reverse-proxy/README.md
infra/wireguard/README.md
packages/README.md
packages/api-contracts/README.md
packages/auth/README.md
packages/config/README.md
packages/domain/README.md
packages/events/README.md
packages/observability/README.md
products/README.md
products/agent-assist/README.md
products/automated-chat/README.md
products/call-intelligence/README.md
products/managed-reception/README.md
products/multichannel-inbox/README.md
products/sales-followup/README.md
services/README.md
services/web-api/README.md
services/web-api/db/README.md
services/voice-runtime/README.md
services/web/voxalia/Dockerfile
services/web/voxalia/README.md
services/web/voxalia/next-env.d.ts
services/web/voxalia/next.config.mjs
services/web/voxalia/package-lock.json
services/web/voxalia/package.json
services/web/voxalia/postcss.config.mjs
services/web/voxalia/tailwind.config.ts
services/web/voxalia/tsconfig.json
services/worker/README.md
verticals/README.md
verticals/_template/README.md
verticals/hospitality/README.md
verticals/hospitality/policies/.gitkeep
verticals/hospitality/prompts/.gitkeep
verticals/hospitality/schemas/.gitkeep
verticals/hospitality/tool-bindings/.gitkeep
verticals/hospitality/workflows/.gitkeep
```
