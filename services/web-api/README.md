# Voxalia Web API

Authoritative API/BFF for Voxalia web applications.

Responsibilities:

- authenticate web sessions;
- resolve user role, active tenant and permissions from PostgreSQL;
- return the effective web menu;
- serve CRUD contracts and mutations for web screens.

This service is the backend boundary for `services/web/voxalia`. Channel
webhooks and provider adapters belong in `channels/*`, not here.
