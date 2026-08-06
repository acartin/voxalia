# BRAIN_MAP

- Generated UTC: `2026-08-06T01:57:10Z`
- Repo root: `/srv/voxalia`
- Git branch: `HETZNER-LOCAL-2026-Agosto-3`
- Git commit: `1742917`
- Policy: high-signal only; Voxalia safeguards, security and context economy.

## 1. Mapa De Intenciones

| Ruta | Responsabilidad | Importancia |
|---|---|---:|
| `compose.yml` | Entrada operativa local: Postgres, Redis, Chatwoot, Voxalia Web, Asterisk propio y FreePBX lab. | 5 |
| `.agent/AI_CONTEXT.md` | Contexto rector de negocio, dominio y arquitectura. | 5 |
| `.agent/ASTERISK_PROVISIONING_RULES.md` | Reglas obligatorias para cerrar BD, UI, render, Apply Config y runtime Asterisk. | 5 |
| `services/web/voxalia` | Consola web Next.js y shell de portal. | 5 |
| `services/web-api` | API/BFF autoritativo para auth, tenant, menu y datos consumidos por la web. | 5 |
| `services/asterisk` | API/provisioner del control plane Asterisk; renderiza desde BD y aplica via AMI. | 5 |
| `services/asterisk-runtime` | Runtime Asterisk directo gestionado por Voxalia, desacoplado de FreePBX. | 5 |
| `services/voice-runtime` | Futuro coordinador de eventos de voz, llamadas y runtime operacional. | 5 |
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
services/asterisk
services/asterisk-runtime
services/asterisk-runtime/config
services/asterisk/app
services/asterisk/db
services/voice-runtime
services/web
services/web-api
services/web-api/app
services/web-api/db
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
.agent/ASTERISK_PROVISIONING_RULES.md
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
docs/operations/crud-and-operational-views-agent-prompt.md
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
services/asterisk-runtime/Dockerfile
services/asterisk-runtime/README.md
services/asterisk-runtime/config/asterisk.conf
services/asterisk-runtime/config/extensions.conf
services/asterisk-runtime/config/http.conf
services/asterisk-runtime/config/pjsip.conf
services/asterisk-runtime/config/queues.conf
services/asterisk-runtime/config/rtp.conf
services/asterisk-runtime/entrypoint.sh
services/asterisk/Dockerfile
services/asterisk/README.md
services/asterisk/app/__init__.py
services/asterisk/app/config.py
services/asterisk/app/db.py
services/asterisk/app/main.py
services/asterisk/requirements.txt
services/voice-runtime/README.md
services/web-api/Dockerfile
services/web-api/README.md
services/web-api/app/__init__.py
services/web-api/app/config.py
services/web-api/app/db.py
services/web-api/app/main.py
services/web-api/app/menu.py
services/web-api/app/security.py
services/web-api/db/README.md
services/web-api/requirements.txt
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
