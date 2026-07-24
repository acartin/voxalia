# AGENTS

## Bootstrap obligatorio por sesion

Antes de implementar, depurar o revisar codigo en `/srv/voxalia`:

1. Leer, en este orden:
   - `.agent/AI_CONTEXT.md`
   - `.agent/RULES.md`
   - `.agent/EXECUTION_MAP.md`
2. Leer `.agent/WEB_UI_STANDARDS.md` si la tarea toca `services/web/voxalia`.
3. Leer ADR relevantes en `docs/adr` solo si la tarea toca arquitectura, contratos, despliegue o decisiones de dominio.
4. Usar `.agent/BRAIN_MAP.md` y `.agent/AI_CONTEXT_PACK.md` como mapa rapido; no recorrer todo el repo salvo necesidad concreta.
5. Regenerar contexto con `bash .agent/regenerar_contexto.sh` solo si aplica:
   - faltan `.agent/BRAIN_MAP.md` o `.agent/AI_CONTEXT_PACK.md`
   - cambio de commit vs `BRAIN_MAP.md`
   - cambio grande en `compose.yml`, `.env.example`, `services/web/voxalia`, `services/api`, `services/voice-runtime`, `channels`, `packages` o `infra`
   - solicitud explicita del usuario

No iniciar cambios de codigo sin ubicar primero la capa afectada y la validacion minima correspondiente.

## Scope operativo actual

Voxalia es un monorepo modular multi-tenant para recepcion telefonica gestionada, comenzando con operacion humana y creciendo hacia multicanal, inteligencia de llamadas y asistencia de IA.

Rutas principales:

- `compose.yml`: entrada operativa local.
- `services/web/voxalia`: consola web Next.js.
- `services/api`: futuro API/BFF autoritativo.
- `services/voice-runtime`: coordinacion de voz propia alrededor de Asterisk.
- `channels`: adaptadores de canales externos, incluyendo Asterisk/Chatwoot/Meta/webchat.
- `connectors`: integraciones externas como PMS, CRM, pagos y correo.
- `packages`: contratos, dominio, auth, eventos, config y observabilidad compartida.
- `infra`: soporte de Asterisk/FreePBX, proxy, despliegue, backups y red.

## Limites innegociables

- Las apps web no acceden directo a PostgreSQL, Asterisk, Chatwoot, FreePBX ni proveedores externos.
- Toda data operativa debe estar scoped por `tenant_id` o equivalente antes de salir del backend.
- El frontend no es fuente autoritativa de tenant, rol, permisos, extensiones SIP ni credenciales.
- Proveedores externos se encapsulan en `channels` o `connectors`; el core usa eventos y contratos propios.
- No copiar patrones de `/srv/datasyncsa` sin revisar si realmente aplican a Voxalia.
