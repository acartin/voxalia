# Voxalia Web API Database

Versioned SQL migrations for the Voxalia-owned application database live in
`migrations/`.

Use the canonical connection declared in `.env`:

```bash
set -a; source .env; set +a
docker exec -i voxalia-postgres psql "$VOXALIA_DATABASE_URL" -v ON_ERROR_STOP=1 -f - < services/web-api/db/migrations/001_auth_security_baseline.sql
```

Administrative grants for pgAdmin and future migrations are applied with the
bootstrap role declared in `.env`:

```bash
set -a; source .env; set +a
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/web-api/db/migrations/002_auth_grants.sql
```

Do not print `VOXALIA_DATABASE_URL` or database passwords in logs. Do not invent
database names, users, hosts or credentials outside `.env` and `.env.example`.

Current migrations:

- `001_auth_security_baseline.sql`: tenants, auth users, roles, permissions, sessions and audit.
- `002_auth_grants.sql`: application/admin database grants.
- `003_tenant_workspace_foundation.sql`: tenant workspace domain tables for products, policies, hours, channels, numbers, contacts, agent assignments, scripts and reporting recipients.
- `004_operations_voice_ai_foundation.sql`: Voxalia-owned conversations, workflow tasks, opportunities, provider mappings, voice call records, recordings, LLM processing, search indexing and operational audit.
- `005_seed_hotel_valle_azul_channels_numbers.sql`: example tenant service policy, channels and numbers/routing rows for Hotel Valle Azul.
- `006_country_catalog.sql`: country catalog for tenant profiles and voice number country dropdowns.
- `007_seed_hotel_valle_azul_contacts.sql`: example tenant contacts and contact methods for Hotel Valle Azul.
