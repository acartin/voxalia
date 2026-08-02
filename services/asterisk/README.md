# Voxalia Asterisk Service

Independent control-plane/provisioning service for Voxalia-owned Asterisk
runtime configuration.

This service owns the Asterisk boundary:

- desired dial contexts for tenant voice namespaces;
- logical extensions that may repeat across tenants;
- queue and route intent for managed reception;
- recording policy application state;
- provisioning jobs, generated config revisions and drift checks;
- runtime/status observations from Asterisk.

It must not become FreePBX. It must not expose SIP secrets or manage FreePBX
internal tables. FreePBX can remain a lab/bootstrap tool, but Voxalia production
should treat Asterisk as the runtime and this service as the reconciler between
Voxalia desired state and applied Asterisk configuration.

Ownership boundary:

```text
Voxalia Web/API
  -> business CRUD and authenticated UI contracts

services/asterisk
  -> Asterisk desired/applied state, provisioning jobs, generated configs,
     adapter diagnostics and runtime observations

Asterisk
  -> executes dialplan, calls, recording and emits events
```

The service may share the Voxalia PostgreSQL database, but its tables live in
the `asterisk` schema and should be managed by migrations in this directory.

## Migrations

Use the bootstrap database role from `.env` without printing secrets. These
migrations create schema objects and grant privileges to the application and
admin roles, so they should not be run with the limited app connection URL.

```bash
set -a; source .env; set +a
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/001_asterisk_control_plane.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/002_tenant_voice_profiles.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/003_dialplan_flow_catalog.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/004_seed_hotel_valle_azul_extensions.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/005_extension_devices.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/006_sip_trunks.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/007_carriers.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/008_trunk_carrier_fk.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/009_asterisk_instances.sql
docker exec -e PGPASSWORD="$POSTGRES_BOOTSTRAP_PASSWORD" -i voxalia-postgres psql -U "$POSTGRES_BOOTSTRAP_USER" -d "$VOXALIA_APP_DB" -v ON_ERROR_STOP=1 -f - < services/asterisk/db/migrations/010_agent_extension_assignments.sql
```
