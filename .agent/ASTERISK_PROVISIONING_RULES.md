# ASTERISK PROVISIONING RULES

## Regla Central

Toda modificacion funcional relacionada con Asterisk debe cerrar el ciclo
completo:

```text
BD Voxalia
  -> API/BFF o API Asterisk
  -> UI/menu correspondiente
  -> render de configuracion
  -> archivos *_voxalia.conf
  -> Apply Config / AMI reload
  -> validacion del runtime
```

No basta con agregar una tabla, campo, CRUD, dropdown, tab o menu. Si ese dato
afecta como Asterisk debe comportarse, tambien debe reflejarse en el render y
en la validacion de provisioning.

## Fuente De Verdad

- Voxalia PostgreSQL es la fuente de verdad.
- `services/asterisk` es el API/provisioner del control plane Asterisk.
- `services/asterisk-runtime` es el runtime Asterisk directo gestionado por
  Voxalia.
- FreePBX queda como laboratorio/referencia; no recibe `Apply Config` y no es
  fuente de verdad para Voxalia.

## Archivos Generados Gestionados Por Voxalia

El provisioner escribe solo archivos Voxalia-owned:

```text
pjsip_voxalia.conf
extensions_voxalia.conf
queues_voxalia.conf
voxalia-routing.preview
voxalia-recording.preview
```

En compose local se escriben desde `voxalia-asterisk-api` en
`VOXALIA_ASTERISK_API_RENDER_OUTPUT_DIR` y se montan en
`voxalia-asterisk-runtime` como `/etc/asterisk/voxalia`.

No editar esos archivos manualmente. Si algo debe cambiar, se cambia en BD,
migracion, API, UI o renderer.

## Checklist Obligatorio Para Cambios Asterisk

Cuando se agregue o modifique cualquier entidad/campo de Asterisk, revisar y
actualizar lo que aplique:

```text
1. Migracion SQL en services/asterisk/db/migrations o services/web-api/db/migrations.
2. Seed de prueba si el flujo necesita datos visibles.
3. Modelos/payloads/endpoints en services/asterisk/app/main.py.
4. Rutas proxy Next en services/web/voxalia/app/api/settings.
5. UI en services/web/voxalia, siguiendo el patron CRUD/workspace existente.
6. Menu/permiso si aparece una pantalla nueva.
7. Dropdowns/FKs para evitar seleccionar registros de otro tenant o scope.
8. render_asterisk_config y helpers de render si el dato afecta runtime.
9. Apply State/pending_details si el dato debe disparar pendiente de aplicar.
10. Overview/Provisioning status si afecta health, runtime o apply.
11. README o .agent si cambia arquitectura, nombres, puertos o responsabilidad.
```

## Campos Que Deben Disparar Pending

Todo campo que pueda cambiar dialplan, endpoints, queues, trunking, routing,
grabacion o comportamiento de llamada debe participar en `last_config_change_at`
y `pending_details`.

Ejemplos:

```text
asterisk.tenant_voice_profiles
asterisk.dial_contexts
asterisk.dialplan_flows
asterisk.dialplan_steps
asterisk.logical_extensions
asterisk.extension_devices
asterisk.logical_queues
asterisk.logical_queue_members
asterisk.routing_rules
asterisk.recording_policies
asterisk.sip_trunks
asterisk.carriers
asterisk.instances
public.voice_numbers
public.tenant_channels
```

Si se agrega una tabla nueva que Asterisk debe consumir, agregarla a esta lista
conceptual y al calculo real de pending/apply state.

## Render Y Apply

El endpoint `POST /api/v1/asterisk/provisioning/apply` debe:

```text
1. Leer la BD actual.
2. Renderizar una revision completa y consistente.
3. Escribir atomicamente los archivos Voxalia-owned.
4. Recargar Asterisk por AMI:
   - dialplan reload
   - pjsip reload
   - queue reload all
5. Registrar job/revision.
6. Dejar el estado en applied solo si el reload fue exitoso.
```

No marcar `applied` si solo se guardo en BD. `applied` significa que Asterisk
acepto el reload del estado renderizado.

## Validacion Minima

Para cambios que afecten provisioning Asterisk:

```bash
docker compose config
docker exec voxalia-asterisk-api python -m py_compile app/main.py app/config.py app/db.py
docker compose up -d --build voxalia-asterisk-api voxalia-asterisk-runtime voxalia-web
curl -sS -X POST http://127.0.0.1:8340/api/v1/asterisk/provisioning/apply \
  -H 'Content-Type: application/json' \
  -d '{"mode":"apply"}'
docker exec voxalia-asterisk-runtime asterisk -rx 'dialplan show <context>'
docker exec voxalia-asterisk-runtime asterisk -rx 'pjsip show endpoints'
docker exec voxalia-asterisk-runtime asterisk -rx 'queue show <queue>'
```

Usar contextos/queues reales del cambio. No imprimir secretos ni `.env`.

## Criterio De UI

- `Save` o `Update` guarda en BD y puede dejar cambios pendientes.
- `Apply Config` aplica el estado completo actual hacia Asterisk.
- El usuario debe poder ver si hay pending/applied/failed.
- Los grids child no deben permitir seleccionar FKs incompatibles con el
  master seleccionado.
- Si una pantalla crea datos que Asterisk usara, debe quedar claro desde donde
  se aplican y como se verifica.
