-- Voxalia country catalog.
-- Idempotent by design: safe to run repeatedly in phase 0 environments.

create table if not exists public.country_catalog (
  country_code text primary key,
  display_name text not null,
  iso_alpha3 text not null,
  phone_country_code text not null default '',
  status text not null default 'active',
  sort_order integer not null default 100,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint country_catalog_country_code_ck check (country_code ~ '^[A-Z]{2}$'),
  constraint country_catalog_iso_alpha3_ck check (iso_alpha3 ~ '^[A-Z]{3}$'),
  constraint country_catalog_status_ck check (status in ('active', 'inactive'))
);

create index if not exists country_catalog_status_sort_idx
  on public.country_catalog(status, sort_order, display_name);

drop trigger if exists country_catalog_set_updated_at on public.country_catalog;
create trigger country_catalog_set_updated_at
before update on public.country_catalog
for each row execute function public.voxalia_set_updated_at();

insert into public.country_catalog (
  country_code, display_name, iso_alpha3, phone_country_code, status, sort_order, metadata
)
values
  ('US', 'United States', 'USA', '+1', 'active', 10, '{"seed":"006_country_catalog"}'::jsonb),
  ('CA', 'Canada', 'CAN', '+1', 'active', 20, '{"seed":"006_country_catalog"}'::jsonb),
  ('MX', 'Mexico', 'MEX', '+52', 'active', 30, '{"seed":"006_country_catalog"}'::jsonb),
  ('CR', 'Costa Rica', 'CRI', '+506', 'active', 40, '{"seed":"006_country_catalog"}'::jsonb)
on conflict (country_code) do update set
  display_name = excluded.display_name,
  iso_alpha3 = excluded.iso_alpha3,
  phone_country_code = excluded.phone_country_code,
  status = excluded.status,
  sort_order = excluded.sort_order,
  metadata = excluded.metadata,
  updated_at = now();

alter table public.tenants
  add column if not exists country_code text not null default 'CR';

update public.tenants
set country_code = 'CR'
where country_code is null;

alter table public.tenants
  drop constraint if exists tenants_country_fk;

alter table public.tenants
  add constraint tenants_country_fk
  foreign key (country_code)
  references public.country_catalog(country_code)
  on update cascade
  on delete restrict;

update public.voice_numbers
set country_code = upper(country_code);

alter table public.voice_numbers
  drop constraint if exists voice_numbers_country_fk;

alter table public.voice_numbers
  add constraint voice_numbers_country_fk
  foreign key (country_code)
  references public.country_catalog(country_code)
  on update cascade
  on delete restrict;

create index if not exists tenants_country_status_idx
  on public.tenants(country_code, status);

create index if not exists voice_numbers_country_status_idx
  on public.voice_numbers(country_code, status);

grant select on public.country_catalog to voxalia_app;
grant select, insert, update, delete on public.country_catalog to voxalia_admin;
