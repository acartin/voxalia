-- Seed logical test extensions for Hotel Valle Azul.
-- These are Voxalia-owned desired-state records; they do not update Asterisk yet.

with tenant_row as (
  select id as tenant_id
  from public.tenants
  where tenant_key = 'hotel-valle-azul'
),
internal_context as (
  select dc.id as dial_context_id, dc.tenant_id
  from asterisk.dial_contexts dc
  join tenant_row t on t.tenant_id = dc.tenant_id
  where dc.context_key = 'internal'
)
insert into asterisk.logical_extensions (
  tenant_id,
  dial_context_id,
  logical_extension,
  display_name,
  extension_type,
  provider_endpoint,
  status,
  config
)
select
  c.tenant_id,
  c.dial_context_id,
  seed.logical_extension,
  seed.display_name,
  seed.extension_type,
  seed.provider_endpoint,
  'active',
  seed.config
from internal_context c
cross join (
  values
    ('3001', 'Valle Azul Reception 3001', 'agent', 'hotel-valle-azul-3001', '{"test_seed":true,"role":"reception"}'::jsonb),
    ('3002', 'Valle Azul Reception 3002', 'agent', 'hotel-valle-azul-3002', '{"test_seed":true,"role":"reception"}'::jsonb),
    ('3003', 'Valle Azul Reservations 3003', 'agent', 'hotel-valle-azul-3003', '{"test_seed":true,"role":"reservations"}'::jsonb),
    ('3004', 'Valle Azul Supervisor 3004', 'supervisor', 'hotel-valle-azul-3004', '{"test_seed":true,"role":"supervisor"}'::jsonb)
) as seed(logical_extension, display_name, extension_type, provider_endpoint, config)
on conflict (tenant_id, dial_context_id, logical_extension) do update set
  display_name = excluded.display_name,
  extension_type = excluded.extension_type,
  provider_endpoint = excluded.provider_endpoint,
  status = excluded.status,
  config = excluded.config,
  updated_at = now();
