-- Seed tenant-owned channel and number examples for Hotel Valle Azul.
-- These are Voxalia core records, not provider-native Chatwoot or Asterisk rows.

do $$
declare
  tenant_id_value bigint;
  policy_id_value bigint;
  toll_free_channel_id bigint;
  local_channel_id bigint;
begin
  select id
  into tenant_id_value
  from public.tenants
  where tenant_key = 'hotel-valle-azul';

  if tenant_id_value is null then
    raise notice 'Tenant hotel-valle-azul not found, skipping channel/number seed.';
    return;
  end if;

  insert into public.tenant_service_policies (
    tenant_id,
    policy_key,
    display_name,
    status,
    default_language,
    supported_languages,
    after_hours_behavior,
    callback_window,
    recording_disclosure,
    recording_retention_days,
    escalation_notes,
    agent_notes,
    metadata
  )
  values (
    tenant_id_value,
    'managed-reception-main',
    'Managed Reception Main Policy',
    'active',
    'en',
    array['en','es']::text[],
    'take_message',
    'Next business day, 08:00-18:00 America/Costa_Rica',
    'This call may be recorded for service quality and follow-up.',
    365,
    'Escalate emergencies and reservation-impacting issues to the operations contact.',
    'Use Hotel Valle Azul greeting, confirm language, capture caller name, phone and request outcome.',
    '{"seed":true,"scenario":"hotel-valle-azul-managed-reception"}'::jsonb
  )
  on conflict (tenant_id, policy_key) do update
  set display_name = excluded.display_name,
      status = excluded.status,
      default_language = excluded.default_language,
      supported_languages = excluded.supported_languages,
      after_hours_behavior = excluded.after_hours_behavior,
      callback_window = excluded.callback_window,
      recording_disclosure = excluded.recording_disclosure,
      recording_retention_days = excluded.recording_retention_days,
      escalation_notes = excluded.escalation_notes,
      agent_notes = excluded.agent_notes,
      metadata = excluded.metadata,
      updated_at = now()
  returning id into policy_id_value;

  insert into public.tenant_channels (
    tenant_id,
    service_policy_id,
    channel_key,
    channel_type,
    display_name,
    provider,
    routing_key,
    default_language,
    status,
    recording_required,
    metadata
  )
  values
    (
      tenant_id_value,
      policy_id_value,
      'main-toll-free',
      'voice_toll_free',
      'Main toll-free reception',
      'asterisk',
      '+18005550100',
      'en',
      'active',
      true,
      '{"seed":true,"routing_intent":"main_reception","asterisk_context":"tenant_hotel_valle_azul_inbound"}'::jsonb
    ),
    (
      tenant_id_value,
      policy_id_value,
      'local-costa-rica',
      'voice_local',
      'Costa Rica local reception',
      'asterisk',
      '+50640001001',
      'es',
      'active',
      true,
      '{"seed":true,"routing_intent":"local_reception","asterisk_context":"tenant_hotel_valle_azul_inbound"}'::jsonb
    ),
    (
      tenant_id_value,
      policy_id_value,
      'chatwoot-front-desk',
      'chatwoot_inbox',
      'Chatwoot front desk inbox',
      'chatwoot',
      'chatwoot-inbox-hva-front-desk',
      'en',
      'provisioning',
      false,
      '{"seed":true,"routing_intent":"front_desk_chat","provider_placeholder":true}'::jsonb
    ),
    (
      tenant_id_value,
      policy_id_value,
      'webchat-booking',
      'voxalia_webchat',
      'Website booking webchat',
      'voxalia',
      'widget-hva-booking',
      'en',
      'provisioning',
      false,
      '{"seed":true,"routing_intent":"booking_webchat","provider_placeholder":true}'::jsonb
    ),
    (
      tenant_id_value,
      policy_id_value,
      'whatsapp-guest-service',
      'meta_whatsapp',
      'WhatsApp guest service',
      'meta',
      '+50660001001',
      'es',
      'provisioning',
      false,
      '{"seed":true,"routing_intent":"guest_service_whatsapp","provider_placeholder":true}'::jsonb
    )
  on conflict (tenant_id, channel_key) do update
  set service_policy_id = excluded.service_policy_id,
      channel_type = excluded.channel_type,
      display_name = excluded.display_name,
      provider = excluded.provider,
      routing_key = excluded.routing_key,
      default_language = excluded.default_language,
      status = excluded.status,
      recording_required = excluded.recording_required,
      metadata = excluded.metadata,
      updated_at = now();

  select id into toll_free_channel_id
  from public.tenant_channels
  where tenant_id = tenant_id_value and channel_key = 'main-toll-free';

  select id into local_channel_id
  from public.tenant_channels
  where tenant_id = tenant_id_value and channel_key = 'local-costa-rica';

  insert into public.voice_numbers (
    tenant_id,
    channel_id,
    number_e164,
    label,
    number_type,
    country_code,
    status,
    recording_required,
    metadata
  )
  values
    (
      tenant_id_value,
      toll_free_channel_id,
      '+18005550100',
      'Main US/Canada toll-free',
      'toll_free',
      'US',
      'active',
      true,
      '{"seed":true,"routing_intent":"main_reception","source":"voxalia-owned"}'::jsonb
    ),
    (
      tenant_id_value,
      local_channel_id,
      '+50640001001',
      'Costa Rica local DID',
      'local',
      'CR',
      'active',
      true,
      '{"seed":true,"routing_intent":"local_reception","source":"voxalia-owned"}'::jsonb
    ),
    (
      tenant_id_value,
      toll_free_channel_id,
      '+18005550101',
      'Outbound caller ID',
      'outbound_caller_id',
      'US',
      'active',
      true,
      '{"seed":true,"routing_intent":"outbound_callback","source":"voxalia-owned"}'::jsonb
    )
  on conflict (number_e164) do update
  set tenant_id = excluded.tenant_id,
      channel_id = excluded.channel_id,
      label = excluded.label,
      number_type = excluded.number_type,
      country_code = excluded.country_code,
      status = excluded.status,
      recording_required = excluded.recording_required,
      metadata = excluded.metadata,
      updated_at = now();

  delete from public.voice_numbers
  where tenant_id = tenant_id_value
    and number_e164 in (
      'chatwoot:chatwoot-inbox-hva-front-desk',
      'webchat:widget-hva-booking',
      '+50660001001'
    )
    and metadata->>'seed' = 'true';
end $$;
