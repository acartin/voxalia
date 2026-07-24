# WEB UI STANDARDS

Aplica a `services/web/voxalia`.

## Principios

- Mantener la consola como herramienta operacional B2B: densa, sobria y orientada a trabajo.
- Reutilizar el shell existente: `components/portal`, `components/ui`, `lib/api.ts`, `lib/modules.ts`.
- No crear landing de marketing dentro de la zona autenticada.
- No conectar la web directo a PostgreSQL, Asterisk, Chatwoot, FreePBX ni proveedores.
- Toda navegacion autenticada debe pasar por menu/permiso resuelto server-side.

## Auth Y Seguridad

- Cookie de sesion httpOnly.
- Logout por POST.
- Placeholder auth solo mientras no exista API real y debe permanecer claramente marcado.
- No guardar credenciales SIP, tokens internos ni datos sensibles en `localStorage`.
- El frontend puede ocultar acciones, pero la autorizacion real vive en backend.

## UI

- Usar iconos funcionales en botones.
- Cards solo para items, estados, modales o paneles de herramienta; no anidar cards.
- Mantener textos en ingles dentro de la app web salvo solicitud explicita de localizacion.
- Estados minimos: loading, empty, error, unauthorized/forbidden y disabled.
- Tema light/dark mediante tokens existentes; no hardcodear colores por pantalla.

## Web Phone Futuro

- El softphone debe ser un componente operacional dentro del shell, no una app aislada.
- Debe exponer estados claros: disconnected, registering, ready, ringing, in-call, reconnecting, failed.
- Debe manejar permisos de microfono, seleccion de dispositivo y errores de media de forma visible y segura.
