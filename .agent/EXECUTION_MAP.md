# EXECUTION MAP

## Decision Rapida

1. Identificar la ruta modificada.
2. Usar la fila correspondiente.
3. Rebuild solo si el codigo se copia en imagen o cambia compose/dependencias.
4. No correr suites pesadas sin razon concreta.

| Ruta | Validacion minima | Rebuild/restart |
|---|---|---|
| `compose.yml` | `docker compose config` | `docker compose up -d --build <servicio>` si cambia build/env/ports |
| `.env.example` | revisar alineacion con `compose.yml` y README | no aplica |
| `.agent/` o `AGENTS.md` | `bash -n .agent/regenerar_contexto.sh` si cambia el script | no aplica |
| `services/web/voxalia/` | `docker build -t voxalia-web:dev services/web/voxalia` desde repo root, o `npm run build` si Node existe en host | `docker compose up -d --build voxalia-web` |
| `services/web-api/` | si hay Python: `python3 -m py_compile`; si hay contenedor futuro, validar dentro del contenedor | segun Dockerfile/compose futuro |
| `services/voice-runtime/` | validar sintaxis del runtime real cuando exista; documentar comandos faltantes mientras sea esqueleto | segun Dockerfile/compose futuro |
| `channels/` | validar adaptador especifico; para Python, `python3 -m py_compile`; para docs, lectura/diff | segun servicio futuro |
| `connectors/` | validar conector especifico; no hacer llamadas reales a proveedores sin permiso | segun servicio futuro |
| `packages/` | validar tests/build del paquete afectado cuando exista | segun consumidor afectado |
| `infra/freepbx/` | `docker compose config`; revisar impacto en FreePBX/Asterisk antes de restart | restart solo con aprobacion o necesidad clara |
| `docs/` | lectura/diff; ADR si cambia decision arquitectonica | no aplica |

## Variables Sensibles

No imprimir valores de:

- `*_PASSWORD`
- `*_SECRET*`
- `*_TOKEN`
- `VOXALIA_DATABASE_URL`
- credenciales SIP/trunks

Variables operativas no secretas que se pueden reportar:

- puertos locales
- nombres de servicios
- nombres de bases/usuarios si ya estan en `.env.example`

## Metodo Correcto Para DB

1. Revisar `.env.example` para ubicar el nombre canonico de la variable.
2. Cargar `.env` solo en el shell del comando:

```bash
set -a; source .env; set +a; <comando>
```

3. Para conexiones a la BD propia de Voxalia, preferir `VOXALIA_DATABASE_URL`.
4. Para tareas administrativas de Postgres, usar `POSTGRES_ADMIN_*` o
   `POSTGRES_BOOTSTRAP_*` segun el caso.
5. No construir URLs de conexion con valores inventados ni pedir credenciales
   que ya esten declaradas en `.env`.
6. No imprimir la URL final ni passwords; validar conectividad con comandos
   silenciosos o salidas sanitizadas.

## Metodo Correcto Para Infraestructura Local

- Usar `compose.yml` como unica entrada operativa local.
- No crear VMs, droplets, contenedores sueltos, redes Docker nuevas ni tuneles
  externos si el usuario no lo pidio explicitamente.
- Si hace falta un componente nuevo, agregarlo primero al modelo de
  configuracion del repo (`compose.yml`, `.env.example`, `infra/*`) y validar
  con `docker compose config`.
