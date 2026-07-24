# Voxalia Web

Service console for Voxalia, created from the reference web stack and theme.

## Responsibility

- Provide the first Voxalia web shell with protected navigation.
- Reuse the same Next.js, TypeScript, Tailwind and component approach as the reference portal.
- Preserve the same authentication shape: login/logout routes, httpOnly session cookie, server-side menu resolution and role-aware shell contracts.
- Consume `services/web-api` for menu, auth, permissions and CRUD data.

## Out Of Scope

- No direct PostgreSQL access from the web app.
- No database model is created in this pass.
- No customer, call, CRM or analytics data is fetched yet.

## Initial Implementation

The app uses Next.js App Router + TypeScript + Tailwind with the shared portal shell.

If `VOXALIA_API_BASE_URL` is not set and `VOXALIA_PLACEHOLDER_AUTH` is not `false`, the app can run in placeholder auth mode for early UI-only work. Product CRUDs must use `services/web-api`.

When the API is ready, set:

```text
VOXALIA_API_BASE_URL=http://voxalia-web-api:8000/api/v1
VOXALIA_PLACEHOLDER_AUTH=false
VOXALIA_SECURE_COOKIES=true
```

Expected API endpoints mirror the reference security contract:

```text
POST /auth/login
POST /auth/logout
POST /auth/forgot-password
POST /auth/reset-password
POST /auth/simulate-role
GET  /menu
GET  /{module-path}
```

## WebRTC Phone Lab

The route `/voice/webrtc-phone` is an experimental browser softphone screen for validating Asterisk WebRTC.

Current lab assumptions:

- the working MicroSIP baseline remains extension `1002`;
- the browser should use the FreePBX-managed WebRTC extension `1004`;
- the default target is `1002` for internal testing;
- the first LAN transport uses `ws://192.168.10.37:8088/ws`; WSS/certificates are a later hardening step;
- SIP password is entered manually and is not stored in local storage;
- recording is expected to be enforced by Asterisk/FreePBX, not by the web app;
- the screen is a technical spike, not the final Operator Console.

Expected first test path:

```text
Voxalia WebRTC 1004
  -> Asterisk / FreePBX
  -> MicroSIP 1002
```
