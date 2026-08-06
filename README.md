# Voxalia

Voxalia is a modular multi-tenant monorepo for managed voice reception,
starting with human-operated hotel phone support and growing toward
multichannel support, call intelligence, and controlled AI assistance.

## Operating Context

Read `.agent/AI_CONTEXT.md` before making architectural or implementation
changes.

## Initial Shape

- `compose.yml` is the main operational entrypoint.
- Infrastructure and packaged platforms run in containers.
- Voxalia-owned apps and services get containers only when implementation or
  deployment needs justify it.
- Provider/channel adapters live in `channels/` and `connectors/`.
- Infrastructure support files live in `infra/`.
- Domain contracts and shared packages live in `packages/`.

## First Commands

```bash
cp .env.example .env
docker compose config
docker compose --profile setup run --rm chatwoot-prepare
docker compose up -d --build
```

Local URLs:

- Chatwoot: `http://localhost:8300`
- FreePBX: `http://localhost:8310`
- FreePBX HTTPS: `https://localhost:8311`
- Voxalia Web: `http://localhost:8320`
- Voxalia Web API: `http://localhost:8330`
- Voxalia Asterisk API: `http://localhost:8340`
- PostgreSQL: `localhost:8432`
- Voxalia-managed Asterisk SIP: `localhost:5060/udp`
- Voxalia-managed Asterisk AMI: `localhost:5038/tcp`
- Voxalia-managed Asterisk HTTP/WebSocket: `localhost:8087/tcp`
- Voxalia-managed Asterisk RTP: `localhost:13000-13100/udp`
- FreePBX lab SIP: `localhost:5062/udp`
- FreePBX lab RTP: `localhost:12000-12100/udp`

Voxalia-managed Asterisk is split into `voxalia-asterisk-runtime`, the actual
Asterisk runtime, and `voxalia-asterisk-api`, the API/provisioner that renders
configuration from Voxalia PostgreSQL and applies it through AMI.

FreePBX remains available only as a lab/reference UI. It is not the source of
truth for Voxalia-owned tenants, contexts, extensions, queues, routing or
recording policies.

## pgAdmin

Use these development connection values for the Voxalia PostgreSQL instance:

```text
Host:     192.168.10.37
Port:     8432
Engine:   PostgreSQL 17 with pgvector
Database: voxalia
User:     voxalia_admin
Password: see POSTGRES_ADMIN_PASSWORD in local .env
```

`voxalia_admin` is for database administration through tools such as pgAdmin.
The future Voxalia application user is `voxalia_app`.

Chatwoot uses the same PostgreSQL container but a separate database:

```text
Database: chatwoot
User:     chatwoot_app
Password: see CHATWOOT_DB_PASSWORD in local .env
```

`chatwoot_app` is a superuser in this local bootstrap because Chatwoot creates
extensions such as `pg_stat_statements` during database preparation.
