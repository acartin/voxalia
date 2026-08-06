#!/usr/bin/env bash
set -euo pipefail

OUT_DIR=".agent"
BRAIN_FILE="$OUT_DIR/BRAIN_MAP.md"
PACK_FILE="$OUT_DIR/AI_CONTEXT_PACK.md"
MAX_FILES="${MAX_FILES:-180}"

mkdir -p "$OUT_DIR"

repo_root="$(pwd)"
now_utc="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo N/A)"
commit="$(git rev-parse --short HEAD 2>/dev/null || echo N/A)"

compose_services() {
  if [[ -f compose.yml ]] && command -v docker >/dev/null 2>&1 && docker compose config --services >/dev/null 2>&1; then
    docker compose config --services
    return
  fi

  awk '
    /^services:/ { in_services=1; next }
    /^[a-zA-Z0-9._-]+:/ { if ($0 !~ /^services:/) in_services=0 }
    in_services && $0 ~ /^  [a-zA-Z0-9._-]+:$/ {
      gsub(":", "", $1)
      print $1
    }
  ' compose.yml 2>/dev/null || true
}

tree_compact() {
  find apps channels connectors docs infra packages products services verticals -maxdepth 2 -type d 2>/dev/null \
    | sort \
    | sed 's#^\./##'
}

files_compact() {
  find apps channels connectors docs infra packages products services verticals -maxdepth 3 -type f 2>/dev/null \
    \( -path '*/node_modules/*' -o -path '*/.next/*' -o -path '*/__pycache__/*' \) -prune -o -type f -print \
    | sort \
    | head -n "$MAX_FILES" \
    | sed 's#^\./##'
}

services="$(compose_services)"
topology="$(tree_compact)"
files="$(files_compact)"

cat > "$BRAIN_FILE" <<EOF
# BRAIN_MAP

- Generated UTC: \`$now_utc\`
- Repo root: \`$repo_root\`
- Git branch: \`$branch\`
- Git commit: \`$commit\`
- Policy: high-signal only; Voxalia safeguards, security and context economy.

## 1. Mapa De Intenciones

| Ruta | Responsabilidad | Importancia |
|---|---|---:|
| \`compose.yml\` | Entrada operativa local: Postgres, Redis, Chatwoot, Voxalia Web, Asterisk propio y FreePBX lab. | 5 |
| \`.agent/AI_CONTEXT.md\` | Contexto rector de negocio, dominio y arquitectura. | 5 |
| \`.agent/ASTERISK_PROVISIONING_RULES.md\` | Reglas obligatorias para cerrar BD, UI, render, Apply Config y runtime Asterisk. | 5 |
| \`services/web/voxalia\` | Consola web Next.js y shell de portal. | 5 |
| \`services/web-api\` | API/BFF autoritativo para auth, tenant, menu y datos consumidos por la web. | 5 |
| \`services/asterisk\` | API/provisioner del control plane Asterisk; renderiza desde BD y aplica via AMI. | 5 |
| \`services/asterisk-runtime\` | Runtime Asterisk directo gestionado por Voxalia, desacoplado de FreePBX. | 5 |
| \`services/voice-runtime\` | Futuro coordinador de eventos de voz, llamadas y runtime operacional. | 5 |
| \`channels\` | Adaptadores de canales externos a contratos internos. | 4 |
| \`connectors\` | Integraciones externas PMS/CRM/pagos/correo. | 4 |
| \`packages\` | Contratos, dominio, auth, eventos, config y observabilidad compartida. | 4 |
| \`infra/freepbx\` | Soporte de FreePBX/Asterisk local. | 4 |
| \`verticals\` | Politicas, prompts, schemas y workflows por vertical. | 3 |

## 2. Limites Criticos

- Apps web no hablan directo con DB, Asterisk, Chatwoot, FreePBX ni proveedores.
- Backend resuelve tenant, rol, permisos, menu y scopes de datos.
- Proveedores viven detras de \`channels\` o \`connectors\`.
- Dominio compartido no contiene condiciones por cliente o vertical.
- Cambios de compose/env deben actualizar \`.env.example\`, README y contexto operativo si aplica.

## 3. Servicios Compose

\`\`\`text
$services
\`\`\`

## 4. Topologia Compacta

\`\`\`text
$topology
\`\`\`

## 5. Archivos De Entrada

\`\`\`text
README.md
.env.example
compose.yml
.agent/AI_CONTEXT.md
.agent/ASTERISK_PROVISIONING_RULES.md
.agent/RULES.md
.agent/EXECUTION_MAP.md
.agent/WEB_UI_STANDARDS.md
$files
\`\`\`
EOF

cat > "$PACK_FILE" <<EOF
# AI Context Pack

- Generated UTC: \`$now_utc\`
- Repo root: \`$repo_root\`
- Git branch: \`$branch\`
- Git commit: \`$commit\`
- Policy: compact; read exact files only when the task needs them.

## Start Here

1. \`.agent/AI_CONTEXT.md\` for product and architecture direction.
2. \`.agent/RULES.md\` for safeguards.
3. \`.agent/EXECUTION_MAP.md\` for validation.
4. \`.agent/ASTERISK_PROVISIONING_RULES.md\` before changing Asterisk DB, menus, CRUDs, renderers or runtime behavior.
5. \`.agent/WEB_UI_STANDARDS.md\` only for \`services/web/voxalia\`.
6. \`.agent/BRAIN_MAP.md\` for routes and file entrypoints.

## Critical Safeguards

- No direct web-to-DB, web-to-Asterisk, web-to-Chatwoot or web-to-provider access.
- Backend/API must own tenant, auth, roles, menu and data scopes.
- No secrets in code, logs, docs or chat output.
- Provider-specific IDs and payloads are translated at adapters/connectors.
- Voice/WebRTC work must consider HTTPS/WSS, mic permissions, NAT, RTP, STUN/TURN and SIP credential exposure.
- Asterisk changes must close BD -> API/UI -> render -> Apply Config -> AMI reload -> runtime validation.
- Regenerate this pack only when structure/commit meaningfully changes.

## Compose Services

\`\`\`text
$services
\`\`\`

## Operational Entry Points

\`\`\`text
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
\`\`\`

## Current Web App Contract

- Route: \`services/web/voxalia\`
- Stack: Next.js, TypeScript, Tailwind.
- Session cookie: \`voxalia_session\`.
- Placeholder auth: enabled when \`VOXALIA_API_BASE_URL\` is empty and \`VOXALIA_PLACEHOLDER_AUTH\` is not \`false\`.
- Default authenticated route: \`/console/overview\`.
- Compose service: \`voxalia-web\`.
- Default port: \`8320\`.

## Validation Shortcuts

\`\`\`bash
docker compose config
docker build -t voxalia-web:dev services/web/voxalia
docker compose up -d --build voxalia-web
bash -n .agent/regenerar_contexto.sh
\`\`\`
EOF

echo "OK: contexto regenerado en $BRAIN_FILE y $PACK_FILE"
