begin;

alter table asterisk.recording_policies
  alter column scope_id drop not null;

insert into asterisk.recording_policies (
  tenant_id,
  policy_key,
  display_name,
  scope_type,
  scope_id,
  recording_required,
  disclosure_required,
  retention_days,
  status,
  config
)
select
  p.tenant_id,
  'default',
  'Default recording policy',
  'tenant',
  null,
  true,
  true,
  365,
  'active',
  '{"created_by":"migration_011"}'::jsonb
from asterisk.tenant_voice_profiles p
join public.tenants t on t.id = p.tenant_id
where p.voice_enabled = true
on conflict (tenant_id, policy_key) do update set
  display_name = excluded.display_name,
  scope_type = excluded.scope_type,
  scope_id = excluded.scope_id,
  recording_required = excluded.recording_required,
  disclosure_required = excluded.disclosure_required,
  retention_days = excluded.retention_days,
  status = excluded.status,
  updated_at = now();

alter table public.tenant_channels
  drop column if exists recording_required;

alter table public.voice_numbers
  drop column if exists recording_required;

alter table asterisk.logical_queues
  drop column if exists recording_required;

alter table asterisk.routing_rules
  drop column if exists recording_required;

commit;
