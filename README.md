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
- PostgreSQL: `localhost:8432`
- Asterisk SIP through FreePBX: `localhost:5062/udp`
- Asterisk RTP through FreePBX: `localhost:12000-12100/udp`

FreePBX is the web interface used to configure trunks, numbers, extensions,
inbound routes, queues, IVR, recordings, and other PBX behavior.

FreePBX/Asterisk uses `America/Costa_Rica` by default for local tests.

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
