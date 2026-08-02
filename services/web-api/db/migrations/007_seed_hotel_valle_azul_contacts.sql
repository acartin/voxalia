-- Seed tenant contacts and contact methods for Hotel Valle Azul.
-- These are tenant operational contacts, not customer/channel entrypoints.

do $$
declare
  tenant_id_value bigint;
  front_desk_id bigint;
  reservations_id bigint;
  general_manager_id bigint;
  emergency_id bigint;
  reporting_id bigint;
  technical_id bigint;
begin
  select id
  into tenant_id_value
  from public.tenants
  where tenant_key = 'hotel-valle-azul';

  if tenant_id_value is null then
    raise notice 'Tenant hotel-valle-azul not found, skipping contacts seed.';
    return;
  end if;

  delete from public.tenant_contact_methods
  where tenant_id = tenant_id_value
    and metadata->>'seed' = 'true'
    and metadata->>'contact_key' in (
      'front-desk',
      'reservations',
      'general-manager',
      'emergency-duty-manager',
      'management-reports',
      'it-support'
    );

  delete from public.tenant_contacts
  where tenant_id = tenant_id_value
    and metadata->>'seed' = 'true'
    and metadata->>'contact_key' in (
      'front-desk',
      'reservations',
      'general-manager',
      'emergency-duty-manager',
      'management-reports',
      'it-support'
    );

  insert into public.tenant_contacts (
    tenant_id,
    display_name,
    organization,
    department,
    title,
    contact_type,
    priority,
    status,
    notes,
    metadata
  )
  values
    (
      tenant_id_value,
      'Front Desk',
      'Hotel Valle Azul',
      'Reception',
      'Front Desk Team',
      'operations',
      10,
      'active',
      'Primary operational contact for guest-facing escalations and reception follow-up.',
      '{"seed":true,"scenario":"hotel-valle-azul-managed-reception","contact_key":"front-desk"}'::jsonb
    ),
    (
      tenant_id_value,
      'Reservations Desk',
      'Hotel Valle Azul',
      'Reservations',
      'Reservations Team',
      'reservations',
      20,
      'active',
      'Use for booking changes, availability questions and reservation-impacting requests.',
      '{"seed":true,"scenario":"hotel-valle-azul-managed-reception","contact_key":"reservations"}'::jsonb
    ),
    (
      tenant_id_value,
      'Laura Mendez',
      'Hotel Valle Azul',
      'Management',
      'General Manager',
      'admin',
      30,
      'active',
      'Escalate service-impacting incidents or account-level concerns.',
      '{"seed":true,"scenario":"hotel-valle-azul-managed-reception","contact_key":"general-manager"}'::jsonb
    ),
    (
      tenant_id_value,
      'Emergency Duty Manager',
      'Hotel Valle Azul',
      'Operations',
      'Duty Manager',
      'emergency',
      5,
      'active',
      'After-hours emergency escalation contact.',
      '{"seed":true,"scenario":"hotel-valle-azul-managed-reception","contact_key":"emergency-duty-manager"}'::jsonb
    ),
    (
      tenant_id_value,
      'Management Reports',
      'Hotel Valle Azul',
      'Management',
      'Reporting Distribution',
      'reporting',
      80,
      'active',
      'Receives weekly call summaries, opportunities and quality notes.',
      '{"seed":true,"scenario":"hotel-valle-azul-managed-reception","contact_key":"management-reports"}'::jsonb
    ),
    (
      tenant_id_value,
      'IT Support',
      'Hotel Valle Azul',
      'Technology',
      'Technical Contact',
      'technical',
      90,
      'active',
      'Use for integration, connectivity and technical follow-up.',
      '{"seed":true,"scenario":"hotel-valle-azul-managed-reception","contact_key":"it-support"}'::jsonb
    )
  ;

  select id into front_desk_id
  from public.tenant_contacts
  where tenant_id = tenant_id_value
    and metadata->>'contact_key' = 'front-desk';

  select id into reservations_id
  from public.tenant_contacts
  where tenant_id = tenant_id_value
    and metadata->>'contact_key' = 'reservations';

  select id into general_manager_id
  from public.tenant_contacts
  where tenant_id = tenant_id_value
    and metadata->>'contact_key' = 'general-manager';

  select id into emergency_id
  from public.tenant_contacts
  where tenant_id = tenant_id_value
    and metadata->>'contact_key' = 'emergency-duty-manager';

  select id into reporting_id
  from public.tenant_contacts
  where tenant_id = tenant_id_value
    and metadata->>'contact_key' = 'management-reports';

  select id into technical_id
  from public.tenant_contacts
  where tenant_id = tenant_id_value
    and metadata->>'contact_key' = 'it-support';

  insert into public.tenant_contact_methods (
    tenant_id,
    contact_id,
    method_type,
    label,
    value,
    is_primary,
    can_receive_escalations,
    availability,
    metadata
  )
  values
    (
      tenant_id_value,
      front_desk_id,
      'phone',
      'Reception desk',
      '+50640001010',
      true,
      true,
      '24/7',
      '{"seed":true,"contact_key":"front-desk"}'::jsonb
    ),
    (
      tenant_id_value,
      front_desk_id,
      'extension',
      'Internal extension',
      '3001',
      false,
      true,
      '24/7',
      '{"seed":true,"contact_key":"front-desk"}'::jsonb
    ),
    (
      tenant_id_value,
      reservations_id,
      'email',
      'Reservations email',
      'reservations@hotelvalleazul.example',
      true,
      false,
      'Business hours',
      '{"seed":true,"contact_key":"reservations"}'::jsonb
    ),
    (
      tenant_id_value,
      reservations_id,
      'phone',
      'Reservations desk',
      '+50640001020',
      false,
      true,
      '08:00-18:00 America/Costa_Rica',
      '{"seed":true,"contact_key":"reservations"}'::jsonb
    ),
    (
      tenant_id_value,
      general_manager_id,
      'email',
      'Manager email',
      'laura.mendez@hotelvalleazul.example',
      true,
      false,
      'Business hours',
      '{"seed":true,"contact_key":"general-manager"}'::jsonb
    ),
    (
      tenant_id_value,
      general_manager_id,
      'whatsapp',
      'Manager WhatsApp',
      '+50660001030',
      false,
      true,
      'Urgent escalations',
      '{"seed":true,"contact_key":"general-manager"}'::jsonb
    ),
    (
      tenant_id_value,
      emergency_id,
      'phone',
      'Emergency duty phone',
      '+50660001999',
      true,
      true,
      '24/7 emergencies only',
      '{"seed":true,"contact_key":"emergency-duty-manager"}'::jsonb
    ),
    (
      tenant_id_value,
      reporting_id,
      'email',
      'Weekly reports',
      'management.reports@hotelvalleazul.example',
      true,
      false,
      'Weekly reporting',
      '{"seed":true,"contact_key":"management-reports"}'::jsonb
    ),
    (
      tenant_id_value,
      technical_id,
      'email',
      'IT support email',
      'it.support@hotelvalleazul.example',
      true,
      false,
      'Business hours',
      '{"seed":true,"contact_key":"it-support"}'::jsonb
    ),
    (
      tenant_id_value,
      technical_id,
      'phone',
      'IT support phone',
      '+50640001090',
      false,
      true,
      'Business hours',
      '{"seed":true,"contact_key":"it-support"}'::jsonb
    )
  on conflict (contact_id, method_type, value) do update
  set label = excluded.label,
      is_primary = excluded.is_primary,
      can_receive_escalations = excluded.can_receive_escalations,
      availability = excluded.availability,
      metadata = excluded.metadata,
      updated_at = now();
end $$;
