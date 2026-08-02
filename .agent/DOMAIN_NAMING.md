# DOMAIN NAMING

## Regla Base

Los nombres de pantalla deben corresponder lo mas posible con el nombre y la
responsabilidad real de la tabla. Evitar alias de UX que oculten el modelo real.

Cuando un recurso aparece en mas de un modulo, solo un modulo debe ser el CRUD
autoritativo. Otros modulos pueden usarlo como FK/dropdown o referencia interna,
pero no deben exponerlo como otro tab si eso sugiere una segunda fuente de
verdad.

## Tenants Y Voz

| Pantalla | Tabla | Responsabilidad |
|---|---|---|
| Tenants | `public.tenants` | Cliente/tenant maestro. |
| Tenant Channels | `public.tenant_channels` | Canales de entrada del tenant. |
| Tenant Contacts | `public.tenant_contacts` | Personas, areas o departamentos del tenant. |
| Contact Methods | `public.tenant_contact_methods` | Telefonos, emails, WhatsApp o extensiones para contactar a una persona/area. |
| Voice Numbers | `public.voice_numbers` | Numeros telefonicos que Voxalia administra para voz y routing. |
| Tenant Voice Profiles | `asterisk.tenant_voice_profiles` | Configuracion telefonica general del tenant. |
| Dial Contexts | `asterisk.dial_contexts` | Contextos de Asterisk dentro del perfil de voz. |
| Routing Rules | `asterisk.routing_rules` | Reglas que conectan canales/numeros/contextos/colas/extensiones. |

## Decision Actual

- `Voice Numbers` vive solamente en `Settings > Tenants > <tenant>`.
- `Settings > Asterisk Tenant Profiles` no tiene tab propio de numeros.
- `Routing Rules` en Asterisk usa `public.voice_numbers` como FK/dropdown.
- Los telefonos administrativos del hotel no son `Voice Numbers`; pertenecen a
  `tenant_contact_methods` asociados a `tenant_contacts`.
