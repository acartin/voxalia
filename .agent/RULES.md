# RULES

## 1. Fuente De Verdad

Orden de precedencia:

1. Codigo ejecutable vigente.
2. `.agent/AI_CONTEXT.md`.
3. `.agent/RULES.md`.
4. `.agent/EXECUTION_MAP.md`.
5. ADR relevantes en `docs/adr`.
6. `.agent/BRAIN_MAP.md` y `.agent/AI_CONTEXT_PACK.md`.

Regenerar contexto solo cuando lo indique `AGENTS.md`. El paquete de contexto es un mapa para ahorrar tokens, no reemplaza la lectura del codigo exacto que se va a tocar.

## 2. Seguridad Y Secretos

- No mostrar `.env` completo ni valores secretos.
- Para validar variables, imprimir solo nombres presentes/ausentes o valores no sensibles como puertos.
- Si un comando necesita `.env`, usar `set -a; source .env; set +a; <comando>` y evitar eco de secretos.
- No hardcodear passwords, tokens, claves SIP, URLs privadas sensibles ni credenciales de proveedores.
- Actualizar `.env.example` cuando se agreguen variables nuevas en compose, apps o servicios.

## 3. Multi-Tenancy

- Toda entidad operacional relevante debe pertenecer a un `tenant_id` o scope equivalente.
- No confiar en `tenant_id`, rol, cliente, extension o permisos enviados libremente por el frontend.
- Todo endpoint de producto debe resolver autorizacion server-side antes de devolver datos.
- Ninguna consulta debe exponer datos cross-tenant por ausencia de filtro.

## 4. Limites De Arquitectura

- `services/web/voxalia` consume APIs propias; no conecta directo a DB, Asterisk, Chatwoot, FreePBX ni proveedores.
- `services/web-api` sera el borde autoritativo para auth, permisos, tenant, menu y datasets livianos consumidos por la web.
- `services/voice-runtime` coordina voz propia; no debe convertirse en UI ni API publica.
- `channels/*` traduce protocolos externos a contratos/eventos internos.
- `connectors/*` encapsula PMS/CRM/pagos/correo y otros proveedores.
- `packages/*` contiene contratos y utilidades compartidas, sin dependencias circulares ni logica especifica de un cliente.
- Logica de verticales vive en `verticals/*`, no en el nucleo compartido.

Regla de oro: si aparece `if tenant == ...` o `if vertical == ...` dentro de dominio compartido, detenerse y mover esa variacion a configuracion, politica, plantilla, vertical o conector.

## 5. Voz, SIP Y WebRTC

- Todas las llamadas gestionadas por Voxalia deben grabarse; una llamada sin grabacion es una excepcion operacional que debe quedar marcada y alertada.
- Las grabaciones son activos sensibles por `tenant_id`: acceso auditado, almacenamiento privado, retencion explicita y uso por IA solo mediante jobs/backend controlados.
- No exponer credenciales SIP permanentes en el navegador.
- El web phone debe usar HTTPS/WSS, permisos explicitos de microfono y contratos backend para provisionar sesion/extension.
- Asterisk/FreePBX se trata como infraestructura critica; cambios deben documentar puertos, codecs, TLS/WSS, NAT, RTP, STUN/TURN y rollback cuando aplique.
- El audio/media no debe pasar por Next.js; la web coordina UI y estado, no transporta RTP.
- Registrar eventos de llamada con IDs internos; IDs de proveedores quedan traducidos por adaptadores.

## 5.1 Asterisk Provisioning

- Leer `.agent/ASTERISK_PROVISIONING_RULES.md` antes de cambiar menus, CRUDs,
  tablas, campos, seeds, endpoints o UI que afecten configuracion de Asterisk.
- Todo dato que afecte runtime Asterisk debe cerrar el ciclo: BD -> API/UI ->
  render -> archivos `*_voxalia.conf` -> `Apply Config` -> AMI reload ->
  validacion runtime.
- No marcar ni asumir `applied` si solo se guardo en BD. `applied` exige que el
  estado renderizado haya sido escrito y recargado exitosamente en Asterisk.
- Si se agrega una tabla/campo que afecta dialplan, PJSIP, queues, routing,
  recording, trunks o runtime, actualizar tambien `render_asterisk_config`,
  el calculo de pending/apply state y la validacion correspondiente.
- FreePBX es laboratorio/referencia; no es fuente de verdad ni destino de
  `Apply Config`.

## 6. Docker, DB Y Operacion

- `compose.yml` es la entrada local principal.
- Validar cambios de compose con `docker compose config`.
- Para DB, usar exclusivamente los parametros definidos en `.env` y
  `.env.example`: `VOXALIA_DATABASE_URL`, `VOXALIA_APP_DB`,
  `VOXALIA_APP_DB_USER`, `VOXALIA_APP_DB_PASSWORD`,
  `POSTGRES_BOOTSTRAP_*` y `POSTGRES_ADMIN_*` segun corresponda.
- Antes de ejecutar SQL, cargar `.env` con `set -a; source .env; set +a` y
  confirmar solo presencia/ausencia de variables criticas, sin revelar valores.
- No inventar hosts, usuarios, passwords, nombres de base ni URLs de conexion
  fuera de `.env`.
- No crear servicios/contenedores nuevos si un modulo o proceso existente cubre el caso.
- No crear maquinas virtuales, droplets, servidores cloud, tuneles externos ni
  recursos de infraestructura fuera de `compose.yml` salvo instruccion explicita
  del usuario.
- Si un cambio toca infraestructura, mantener alineados `README.md`, `.env.example` y `.agent/*` relevante.

## 7. Validacion Minima

Usar `.agent/EXECUTION_MAP.md` para decidir validacion.

Si no se pudo validar, reportar exactamente que falto y por que.
