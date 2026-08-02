import json
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.db import db

app = FastAPI(title="Voxalia Asterisk Service")


class DialplanFlowPayload(BaseModel):
    context_key: str = Field(min_length=1)
    flow_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    entry_extension: str = Field(default="s", min_length=1)
    status: str = "active"
    version: int = Field(default=1, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DialplanStepPayload(BaseModel):
    flow_id: int = Field(gt=0)
    step_order: int = Field(gt=0)
    action_key: str = Field(min_length=1)
    label: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class LogicalExtensionPayload(BaseModel):
    context_key: str = Field(min_length=1)
    logical_extension: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    extension_type: str = "agent"
    provider_endpoint: str = Field(min_length=1)
    status: str = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class LogicalQueuePayload(BaseModel):
    context_key: str = Field(min_length=1)
    queue_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    provider_queue_name: str = Field(min_length=1)
    strategy: str = "ringall"
    timeout_seconds: int = Field(default=30, gt=0)
    recording_required: bool = True
    status: str = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class QueueMemberPayload(BaseModel):
    queue_key: str = Field(min_length=1)
    extension_id: int = Field(gt=0)
    penalty: int = Field(default=0, ge=0)
    status: str = "active"


class ExtensionDevicePayload(BaseModel):
    extension_id: int = Field(gt=0)
    device_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    device_type: str = "web_phone"
    provider_endpoint: str = Field(min_length=1)
    registration_mode: str = "managed_app"
    status: str = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class RoutingRulePayload(BaseModel):
    channel_id: int | None = None
    number_id: int | None = None
    inbound_context_id: int | None = None
    target_type: str = Field(pattern="^(queue|extension|context|external_number|voicemail|hangup)$")
    target_id: str = Field(min_length=1, max_length=240)
    priority: int = Field(default=100, ge=0)
    recording_required: bool = True
    status: str = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class SipTrunkPayload(BaseModel):
    trunk_key: str = Field(min_length=1, max_length=120, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(min_length=1, max_length=160)
    carrier_key: str = Field(min_length=1, max_length=120)
    provider_endpoint: str = Field(min_length=1, max_length=240)
    transport: str = "udp"
    trunk_role: str = "bidirectional"
    registration_mode: str = "outbound_registration"
    auth_mode: str = "outbound_auth"
    match_strategy: str = "ip"
    remote_hosts: str = ""
    codecs: str = "ulaw,alaw"
    max_channels: int = Field(default=0, ge=0)
    status: str = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class CarrierPayload(BaseModel):
    carrier_key: str = Field(min_length=1, max_length=120, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(min_length=1, max_length=160)
    provider_name: str = Field(min_length=1, max_length=160)
    account_scope: str = "global"
    region: str = Field(default="us", min_length=1, max_length=80)
    support_status: str = "standard"
    failover_policy: str = "manual"
    status: str = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class AsteriskInstancePayload(BaseModel):
    instance_key: str = Field(min_length=1, max_length=120, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(min_length=1, max_length=160)
    environment: str = "dev"
    role: str = "standalone"
    control_mode: str = "config_render"
    endpoint_ref: str = Field(min_length=1, max_length=240)
    region: str = Field(default="local", min_length=1, max_length=80)
    asterisk_version: str = Field(default="", max_length=80)
    capabilities: str = "pjsip,queues,recording"
    status: str = "active"
    health_status: str = "unknown"
    config: dict[str, Any] = Field(default_factory=dict)


def parse_json_object(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Expected a JSON object")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "voxalia-asterisk"}


@app.get("/api/v1/asterisk/overview")
def overview() -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  (select count(*)::int from asterisk.dial_contexts where status = 'active') as active_contexts,
                  (select count(*)::int from asterisk.logical_extensions where status = 'active') as active_extensions,
                  (select count(*)::int from asterisk.logical_queues where status = 'active') as active_queues,
                  (select count(*)::int from asterisk.provisioning_jobs where status in ('queued', 'running')) as pending_jobs,
                  (select count(*)::int from asterisk.drift_checks where status in ('drift_detected', 'failed')) as drift_alerts;
                """
            )
            counts = cursor.fetchone()

    return {"status": "ok", "summary": counts}


@app.get("/api/v1/asterisk/workspace")
def workspace() -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  (select count(*)::int from public.tenants where status = 'active') as tenants,
                  (select count(*)::int from asterisk.dial_contexts where status = 'active') as contexts,
                  (select count(*)::int from asterisk.logical_extensions where status = 'active') as extensions,
                  (select count(*)::int from asterisk.logical_queues where status = 'active') as queues,
                  (select count(*)::int from asterisk.routing_rules where status = 'active') as routes,
                  (select count(*)::int from asterisk.recording_policies where status = 'active') as recording_policies,
                  (select count(*)::int from asterisk.provisioning_jobs where status in ('queued', 'running')) as pending_jobs,
                  (select count(*)::int from asterisk.drift_checks where status in ('drift_detected', 'failed')) as drift_alerts;
                """
            )
            counts = cursor.fetchone()

            cursor.execute(
                """
                select tenant_key, display_name
                from public.tenants
                where status = 'active'
                order by id asc
                limit 5;
                """
            )
            tenants = [dict(row) for row in cursor.fetchall()]

    sections = [
        {"id": "overview", "label": "Overview", "description": "Control-plane health, active tenant namespaces and provisioning posture.", "status": "live", "component": "summary", "records": tenants},
        {"id": "tenants", "label": "Tenants", "description": "Tenant voice namespaces managed by Voxalia before rendering Asterisk configuration.", "status": "planned-crud", "component": "crud-grid", "records": []},
        {"id": "contexts", "label": "Contexts", "description": "Inbound, internal, outbound, queue and after-hours dialplan namespaces per tenant.", "status": "planned-crud", "component": "crud-grid", "records": []},
        {"id": "extensions", "label": "Extensions", "description": "Logical tenant extensions such as 3001 and 3002 mapped to unique provider endpoints.", "status": "planned-crud", "component": "crud-grid", "records": []},
        {"id": "queues", "label": "Queues", "description": "Managed reception queues and queue membership intent generated from Voxalia state.", "status": "planned-crud", "component": "crud-grid", "records": []},
        {"id": "routing", "label": "Routing", "description": "DID, channel and after-hours routing rules without editing FreePBX internals.", "status": "planned-crud", "component": "crud-grid", "records": []},
        {"id": "recording", "label": "Recording", "description": "Recording policy intent, retention and disclosure state applied to Asterisk runtime.", "status": "planned-crud", "component": "crud-grid", "records": []},
        {"id": "provisioning", "label": "Provisioning", "description": "Render, apply, reload and rollback jobs for generated Asterisk configuration.", "status": "technical-view", "component": "operational-view", "records": []},
        {"id": "revisions", "label": "Revisions", "description": "Generated configuration revisions, active hashes and rollback candidates.", "status": "technical-view", "component": "operational-view", "records": []},
        {"id": "mappings", "label": "Mappings", "description": "Provider object mappings for contexts, DIDs, queues, endpoints and recording paths.", "status": "technical-view", "component": "operational-view", "records": []},
        {"id": "drift", "label": "Drift", "description": "Checks that compare desired Voxalia state with the applied Asterisk runtime state.", "status": "technical-view", "component": "operational-view", "records": []},
        {"id": "runtime", "label": "Runtime", "description": "Asterisk instance health, version, last seen timestamp and adapter diagnostics.", "status": "technical-view", "component": "operational-view", "records": []},
    ]

    return {
        "workspace": {"id": "settings.asterisk", "title": "Asterisk Control Plane", "status": "Live"},
        "subject": {
            "id": "asterisk",
            "key": "asterisk",
            "title": "Asterisk",
            "subtitle": "Tenant-aware voice provisioning, contexts, routing, recording and runtime diagnostics.",
            "status": "active",
            "badges": ["Asterisk direct", "FreePBX lab compatible"],
        },
        "context": {"client_id": "system", "role": "system_admin"},
        "links": {},
        "actions": [],
        "summary": [
            {"label": "Tenants", "value": counts["tenants"], "tone": "blue"},
            {"label": "Contexts", "value": counts["contexts"], "tone": "green"},
            {"label": "Extensions", "value": counts["extensions"], "tone": "amber"},
            {"label": "Devices", "value": counts["extension_devices"], "tone": "blue"},
            {"label": "Queues", "value": counts["queues"], "tone": "blue"},
            {"label": "Routes", "value": counts["routes"], "tone": "green"},
            {"label": "Recording", "value": counts["recording_policies"], "tone": "amber"},
            {"label": "Jobs", "value": counts["pending_jobs"], "tone": "red"},
            {"label": "Drift", "value": counts["drift_alerts"], "tone": "red"},
        ],
        "sections": sections,
    }


@app.get("/api/v1/asterisk/tenants")
def tenant_profiles() -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  p.id::text,
                  t.id::text as tenant_id,
                  t.tenant_key,
                  t.display_name as tenant_name,
                  p.voice_enabled,
                  p.provisioning_mode,
                  p.namespace_key,
                  p.default_context_prefix,
                  p.default_extension_prefix,
                  p.status,
                  count(distinct dc.id)::int as contexts,
                  count(distinct le.id)::int as extensions,
                  count(distinct ed.id)::int as extension_devices,
                  count(distinct lq.id)::int as queues,
                  count(distinct rr.id)::int as routes,
                  count(distinct rp.id)::int as recording_policies,
                  p.last_provisioned_at::text,
                  p.last_drift_check_at::text
                from asterisk.tenant_voice_profiles p
                join public.tenants t on t.id = p.tenant_id
                left join asterisk.dial_contexts dc on dc.tenant_id = p.tenant_id
                left join asterisk.logical_extensions le on le.tenant_id = p.tenant_id
                left join asterisk.extension_devices ed on ed.tenant_id = p.tenant_id
                left join asterisk.logical_queues lq on lq.tenant_id = p.tenant_id
                left join asterisk.routing_rules rr on rr.tenant_id = p.tenant_id
                left join asterisk.recording_policies rp on rp.tenant_id = p.tenant_id
                group by p.id, t.id, t.tenant_key, t.display_name
                order by t.display_name asc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]

    return {
        "module": {
            "id": "settings.asterisk",
            "title": "Asterisk Tenant Profiles",
            "description": "Tenant voice profiles, assigned numbers, contexts, routing, recording and provisioning.",
            "status": "Live",
        },
        "context": {"client_id": "system", "role": "system_admin"},
        "links": {},
        "actions": [],
        "records": records,
    }


@app.get("/api/v1/asterisk/infrastructure/trunks")
def sip_trunks() -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select carrier_key as value, display_name as label
                from asterisk.carriers
                where status = 'active'
                order by display_name asc, id asc;
                """
            )
            carrier_options = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select
                  st.id::text,
                  st.trunk_key,
                  st.display_name,
                  st.carrier_key,
                  coalesce(c.display_name, st.carrier_name, '') as carrier_name,
                  st.provider_endpoint,
                  st.transport,
                  st.trunk_role,
                  st.registration_mode,
                  st.auth_mode,
                  st.match_strategy,
                  st.remote_hosts,
                  st.codecs,
                  st.max_channels,
                  st.status,
                  st.config,
                  st.updated_at::text
                from asterisk.sip_trunks st
                left join asterisk.carriers c on c.carrier_key = st.carrier_key
                order by st.display_name asc, st.id asc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]
            for record in records:
                record["_carrier_options"] = carrier_options

    return {
        "module": {
            "id": "settings.asterisk.infrastructure.trunks",
            "title": "SIP Trunks",
            "description": "Global PJSIP trunk intent rendered later into endpoint, aor, auth, registration and identify objects.",
            "status": "Live",
        },
        "context": {"client_id": "system", "role": "system_admin"},
        "links": {},
        "actions": [{"id": "create", "label": "Create trunk", "enabled": True, "permission": "voice:configure"}],
        "filters": {"carrier_options": carrier_options},
        "records": records,
    }


@app.post("/api/v1/asterisk/infrastructure/trunks", status_code=status.HTTP_201_CREATED)
def create_sip_trunk(payload: SipTrunkPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into asterisk.sip_trunks (
                  trunk_key, display_name, carrier_key, carrier_name, provider_endpoint, transport,
                  trunk_role, registration_mode, auth_mode, match_strategy, remote_hosts,
                  codecs, max_channels, status, config
                )
                values (
                  %(trunk_key)s, %(display_name)s, %(carrier_key)s, %(carrier_name)s, %(provider_endpoint)s, %(transport)s,
                  %(trunk_role)s, %(registration_mode)s, %(auth_mode)s, %(match_strategy)s, %(remote_hosts)s,
                  %(codecs)s, %(max_channels)s, %(status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "trunk_key": payload.trunk_key,
                    "display_name": payload.display_name,
                    "carrier_key": payload.carrier_key,
                    "carrier_name": payload.carrier_key,
                    "provider_endpoint": payload.provider_endpoint,
                    "transport": payload.transport,
                    "trunk_role": payload.trunk_role,
                    "registration_mode": payload.registration_mode,
                    "auth_mode": payload.auth_mode,
                    "match_strategy": payload.match_strategy,
                    "remote_hosts": payload.remote_hosts,
                    "codecs": payload.codecs,
                    "max_channels": payload.max_channels,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/infrastructure/trunks/{trunk_id}")
def update_sip_trunk(trunk_id: int, payload: SipTrunkPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update asterisk.sip_trunks
                set
                  trunk_key = %(trunk_key)s,
                  display_name = %(display_name)s,
                  carrier_key = %(carrier_key)s,
                  carrier_name = %(carrier_name)s,
                  provider_endpoint = %(provider_endpoint)s,
                  transport = %(transport)s,
                  trunk_role = %(trunk_role)s,
                  registration_mode = %(registration_mode)s,
                  auth_mode = %(auth_mode)s,
                  match_strategy = %(match_strategy)s,
                  remote_hosts = %(remote_hosts)s,
                  codecs = %(codecs)s,
                  max_channels = %(max_channels)s,
                  status = %(status)s,
                  config = %(config)s::jsonb
                where id = %(id)s
                returning id::text;
                """,
                {
                    "id": trunk_id,
                    "trunk_key": payload.trunk_key,
                    "display_name": payload.display_name,
                    "carrier_key": payload.carrier_key,
                    "carrier_name": payload.carrier_key,
                    "provider_endpoint": payload.provider_endpoint,
                    "transport": payload.transport,
                    "trunk_role": payload.trunk_role,
                    "registration_mode": payload.registration_mode,
                    "auth_mode": payload.auth_mode,
                    "match_strategy": payload.match_strategy,
                    "remote_hosts": payload.remote_hosts,
                    "codecs": payload.codecs,
                    "max_channels": payload.max_channels,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SIP trunk not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/infrastructure/trunks/{trunk_id}")
def delete_sip_trunk(trunk_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from asterisk.sip_trunks
                where id = %(id)s
                returning id::text;
                """,
                {"id": trunk_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SIP trunk not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.get("/api/v1/asterisk/infrastructure/carriers")
def carriers() -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  id::text,
                  carrier_key,
                  display_name,
                  provider_name,
                  account_scope,
                  region,
                  support_status,
                  failover_policy,
                  status,
                  config,
                  updated_at::text
                from asterisk.carriers
                order by display_name asc, id asc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]

    return {
        "module": {
            "id": "settings.asterisk.infrastructure.carriers",
            "title": "Carriers",
            "description": "Global provider account catalog used to organize Asterisk trunk connectivity.",
            "status": "Live",
        },
        "context": {"client_id": "system", "role": "system_admin"},
        "links": {},
        "actions": [{"id": "create", "label": "Create carrier", "enabled": True, "permission": "voice:configure"}],
        "records": records,
    }


@app.post("/api/v1/asterisk/infrastructure/carriers", status_code=status.HTTP_201_CREATED)
def create_carrier(payload: CarrierPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into asterisk.carriers (
                  carrier_key, display_name, provider_name, account_scope, region,
                  support_status, failover_policy, status, config
                )
                values (
                  %(carrier_key)s, %(display_name)s, %(provider_name)s, %(account_scope)s, %(region)s,
                  %(support_status)s, %(failover_policy)s, %(status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "carrier_key": payload.carrier_key,
                    "display_name": payload.display_name,
                    "provider_name": payload.provider_name,
                    "account_scope": payload.account_scope,
                    "region": payload.region,
                    "support_status": payload.support_status,
                    "failover_policy": payload.failover_policy,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/infrastructure/carriers/{carrier_id}")
def update_carrier(carrier_id: int, payload: CarrierPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update asterisk.carriers
                set
                  carrier_key = %(carrier_key)s,
                  display_name = %(display_name)s,
                  provider_name = %(provider_name)s,
                  account_scope = %(account_scope)s,
                  region = %(region)s,
                  support_status = %(support_status)s,
                  failover_policy = %(failover_policy)s,
                  status = %(status)s,
                  config = %(config)s::jsonb
                where id = %(id)s
                returning id::text;
                """,
                {
                    "id": carrier_id,
                    "carrier_key": payload.carrier_key,
                    "display_name": payload.display_name,
                    "provider_name": payload.provider_name,
                    "account_scope": payload.account_scope,
                    "region": payload.region,
                    "support_status": payload.support_status,
                    "failover_policy": payload.failover_policy,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrier not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/infrastructure/carriers/{carrier_id}")
def delete_carrier(carrier_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from asterisk.carriers
                where id = %(id)s
                returning id::text;
                """,
                {"id": carrier_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carrier not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.get("/api/v1/asterisk/infrastructure/instances")
def asterisk_instances() -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  id::text,
                  instance_key,
                  display_name,
                  environment,
                  role,
                  control_mode,
                  endpoint_ref,
                  region,
                  asterisk_version,
                  capabilities,
                  status,
                  health_status,
                  last_seen_at::text,
                  config,
                  updated_at::text
                from asterisk.instances
                order by environment asc, display_name asc, id asc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]

    return {
        "module": {
            "id": "settings.asterisk.infrastructure.instances",
            "title": "Asterisk Instances",
            "description": "Global Asterisk runtime node inventory for provisioning targets and health posture.",
            "status": "Live",
        },
        "context": {"client_id": "system", "role": "system_admin"},
        "links": {},
        "actions": [{"id": "create", "label": "Create instance", "enabled": True, "permission": "voice:configure"}],
        "records": records,
    }


@app.post("/api/v1/asterisk/infrastructure/instances", status_code=status.HTTP_201_CREATED)
def create_asterisk_instance(payload: AsteriskInstancePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into asterisk.instances (
                  instance_key, display_name, environment, role, control_mode, endpoint_ref,
                  region, asterisk_version, capabilities, status, health_status, config
                )
                values (
                  %(instance_key)s, %(display_name)s, %(environment)s, %(role)s, %(control_mode)s, %(endpoint_ref)s,
                  %(region)s, %(asterisk_version)s, %(capabilities)s, %(status)s, %(health_status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "instance_key": payload.instance_key,
                    "display_name": payload.display_name,
                    "environment": payload.environment,
                    "role": payload.role,
                    "control_mode": payload.control_mode,
                    "endpoint_ref": payload.endpoint_ref,
                    "region": payload.region,
                    "asterisk_version": payload.asterisk_version,
                    "capabilities": payload.capabilities,
                    "status": payload.status,
                    "health_status": payload.health_status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/infrastructure/instances/{instance_id}")
def update_asterisk_instance(instance_id: int, payload: AsteriskInstancePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                update asterisk.instances
                set
                  instance_key = %(instance_key)s,
                  display_name = %(display_name)s,
                  environment = %(environment)s,
                  role = %(role)s,
                  control_mode = %(control_mode)s,
                  endpoint_ref = %(endpoint_ref)s,
                  region = %(region)s,
                  asterisk_version = %(asterisk_version)s,
                  capabilities = %(capabilities)s,
                  status = %(status)s,
                  health_status = %(health_status)s,
                  config = %(config)s::jsonb
                where id = %(id)s
                returning id::text;
                """,
                {
                    "id": instance_id,
                    "instance_key": payload.instance_key,
                    "display_name": payload.display_name,
                    "environment": payload.environment,
                    "role": payload.role,
                    "control_mode": payload.control_mode,
                    "endpoint_ref": payload.endpoint_ref,
                    "region": payload.region,
                    "asterisk_version": payload.asterisk_version,
                    "capabilities": payload.capabilities,
                    "status": payload.status,
                    "health_status": payload.health_status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asterisk instance not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/infrastructure/instances/{instance_id}")
def delete_asterisk_instance(instance_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from asterisk.instances
                where id = %(id)s
                returning id::text;
                """,
                {"id": instance_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asterisk instance not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


def fetch_records(cursor, query: str, params: int | dict[str, object]) -> list[dict[str, object]]:
    query_params = {"tenant_id": params} if isinstance(params, int) else params
    cursor.execute(query, query_params)
    return [dict(row) for row in cursor.fetchall()]


def tenant_id_for_key(cursor, tenant_key: str) -> int:
    cursor.execute("select id from public.tenants where tenant_key = %(tenant_key)s;", {"tenant_key": tenant_key})
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return int(row["id"])


def context_id_for_key(cursor, tenant_id: int, context_key: str) -> int:
    cursor.execute(
        """
        select id
        from asterisk.dial_contexts
        where tenant_id = %(tenant_id)s and context_key = %(context_key)s;
        """,
        {"tenant_id": tenant_id, "context_key": context_key},
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dial context not found")
    return int(row["id"])


def ensure_flow_id(cursor, tenant_id: int, flow_id: int) -> int:
    cursor.execute(
        """
        select id
        from asterisk.dialplan_flows
        where tenant_id = %(tenant_id)s and id = %(flow_id)s;
        """,
        {"tenant_id": tenant_id, "flow_id": flow_id},
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialplan flow not found")
    return int(row["id"])


def queue_id_for_key(cursor, tenant_id: int, queue_key: str) -> int:
    cursor.execute(
        """
        select id
        from asterisk.logical_queues
        where tenant_id = %(tenant_id)s and queue_key = %(queue_key)s;
        """,
        {"tenant_id": tenant_id, "queue_key": queue_key},
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logical queue not found")
    return int(row["id"])


def ensure_extension_id(cursor, tenant_id: int, extension_id: int) -> int:
    cursor.execute(
        """
        select id
        from asterisk.logical_extensions
        where tenant_id = %(tenant_id)s and id = %(extension_id)s;
        """,
        {"tenant_id": tenant_id, "extension_id": extension_id},
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logical extension not found")
    return int(row["id"])


def ensure_channel_id(cursor, tenant_id: int, channel_id: int | None) -> None:
    if channel_id is None:
        return
    cursor.execute(
        """
        select id
        from public.tenant_channels
        where tenant_id = %(tenant_id)s and id = %(channel_id)s;
        """,
        {"tenant_id": tenant_id, "channel_id": channel_id},
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown channel for tenant")


def ensure_number_id(cursor, tenant_id: int, number_id: int | None) -> None:
    if number_id is None:
        return
    cursor.execute(
        """
        select id
        from public.voice_numbers
        where tenant_id = %(tenant_id)s and id = %(number_id)s;
        """,
        {"tenant_id": tenant_id, "number_id": number_id},
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown number for tenant")


def ensure_context_id(cursor, tenant_id: int, context_id: int | None) -> None:
    if context_id is None:
        return
    cursor.execute(
        """
        select id
        from asterisk.dial_contexts
        where tenant_id = %(tenant_id)s and id = %(context_id)s;
        """,
        {"tenant_id": tenant_id, "context_id": context_id},
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown context for tenant")


def ensure_route_target(cursor, tenant_id: int, target_type: str, target_id: str) -> None:
    if target_type == "queue":
        cursor.execute(
            "select id from asterisk.logical_queues where tenant_id = %(tenant_id)s and queue_key = %(target_id)s;",
            {"tenant_id": tenant_id, "target_id": target_id},
        )
    elif target_type == "extension":
        cursor.execute(
            "select id from asterisk.logical_extensions where tenant_id = %(tenant_id)s and logical_extension = %(target_id)s;",
            {"tenant_id": tenant_id, "target_id": target_id},
        )
    elif target_type == "context":
        cursor.execute(
            "select id from asterisk.dial_contexts where tenant_id = %(tenant_id)s and context_key = %(target_id)s;",
            {"tenant_id": tenant_id, "target_id": target_id},
        )
    else:
        return

    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown {target_type} target for tenant")


@app.get("/api/v1/asterisk/tenants/{tenant_key}/workspace")
def tenant_workspace(tenant_key: str) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  t.id,
                  t.id::text as id_text,
                  t.tenant_key,
                  t.display_name,
                  t.vertical,
                  t.timezone,
                  t.status as tenant_status,
                  p.voice_enabled,
                  p.provisioning_mode,
                  p.namespace_key,
                  p.default_context_prefix,
                  p.default_extension_prefix,
                  p.status as voice_status,
                  p.last_provisioned_at::text,
                  p.last_drift_check_at::text
                from public.tenants t
                join asterisk.tenant_voice_profiles p on p.tenant_id = t.id
                where t.tenant_key = %(tenant_key)s;
                """,
                {"tenant_key": tenant_key},
            )
            profile = cursor.fetchone()
            if not profile:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asterisk tenant profile not found")

            tenant_id = profile["id"]
            cursor.execute(
                """
                select
                  (select count(*)::int from asterisk.dial_contexts where tenant_id = %(tenant_id)s) as contexts,
                  (select count(*)::int from asterisk.logical_extensions where tenant_id = %(tenant_id)s) as extensions,
                  (select count(*)::int from asterisk.extension_devices where tenant_id = %(tenant_id)s) as extension_devices,
                  (select count(*)::int from asterisk.logical_queues where tenant_id = %(tenant_id)s) as queues,
                  (select count(*)::int from asterisk.dialplan_flows where tenant_id = %(tenant_id)s and status = 'active') as flows,
                  (select count(*)::int from asterisk.dialplan_steps where tenant_id = %(tenant_id)s and status = 'active') as steps,
                  (select count(*)::int from asterisk.routing_rules where tenant_id = %(tenant_id)s) as routes,
                  (select count(*)::int from asterisk.recording_policies where tenant_id = %(tenant_id)s) as recording_policies,
                  (select count(*)::int from asterisk.provisioning_jobs where tenant_id = %(tenant_id)s and status in ('queued', 'running')) as pending_jobs,
                  (select count(*)::int from asterisk.drift_checks where tenant_id = %(tenant_id)s and status in ('drift_detected', 'failed')) as drift_alerts;
                """,
                {"tenant_id": tenant_id},
            )
            counts = cursor.fetchone()

            contexts = fetch_records(
                cursor,
                """
                select
                  dc.context_key,
                  dc.display_name,
                  dc.provider_context_name,
                  dc.direction,
                  dc.status,
                  count(distinct f.id)::int as flows
                from asterisk.dial_contexts
                dc
                left join asterisk.dialplan_flows f on f.dial_context_id = dc.id
                where dc.tenant_id = %(tenant_id)s
                group by dc.id, dc.context_key, dc.display_name, dc.provider_context_name, dc.direction, dc.status
                order by dc.context_key asc;
                """,
                {"tenant_id": tenant_id, "tenant_key": profile["tenant_key"]},
            )
            flows = fetch_records(
                cursor,
                """
                select
                  f.id::text,
                  dc.context_key,
                  f.flow_key,
                  f.display_name,
                  f.entry_extension,
                  f.status,
                  f.version,
                  f.metadata,
                  count(s.id)::int as steps,
                  jsonb_build_array(
                    jsonb_build_object('label', 'Flow Steps', 'href', '/settings/asterisk/' || %(tenant_key)s || '?tab=flow-steps&flow_id=' || f.id::text)
                  ) as _actions
                from asterisk.dialplan_flows f
                join asterisk.dial_contexts dc on dc.id = f.dial_context_id
                left join asterisk.dialplan_steps s on s.dialplan_flow_id = f.id
                where f.tenant_id = %(tenant_id)s
                group by dc.context_key, f.id, f.flow_key, f.display_name, f.entry_extension, f.status, f.version, f.metadata
                order by dc.context_key asc, f.flow_key asc;
                """,
                {"tenant_id": tenant_id, "tenant_key": profile["tenant_key"]},
            )
            flow_steps = fetch_records(
                cursor,
                """
                select s.id::text, s.dialplan_flow_id::text as flow_id, dc.context_key, f.flow_key, s.step_order, s.action_key, s.label, s.parameters, s.status
                from asterisk.dialplan_steps s
                join asterisk.dialplan_flows f on f.id = s.dialplan_flow_id
                join asterisk.dial_contexts dc on dc.id = f.dial_context_id
                where s.tenant_id = %(tenant_id)s
                order by dc.context_key asc, f.flow_key asc, s.step_order asc;
                """,
                tenant_id,
            )
            cursor.execute(
                """
                select context_key as value, display_name as label
                from asterisk.dial_contexts
                where tenant_id = %(tenant_id)s
                order by context_key asc;
                """,
                {"tenant_id": tenant_id},
            )
            context_options = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select f.id::text as value, dc.context_key || ' / ' || f.display_name as label
                from asterisk.dialplan_flows f
                join asterisk.dial_contexts dc on dc.id = f.dial_context_id
                where f.tenant_id = %(tenant_id)s
                order by dc.context_key asc, f.flow_key asc;
                """,
                {"tenant_id": tenant_id},
            )
            flow_options = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select action_key as value, label
                from asterisk.dialplan_action_catalog
                where status = 'active'
                order by category asc, action_key asc;
                """,
            )
            action_options = [dict(row) for row in cursor.fetchall()]
            extensions = fetch_records(
                cursor,
                """
                select
                  le.id::text,
                  dc.context_key,
                  le.logical_extension,
                  le.display_name,
                  le.extension_type,
                  le.provider_endpoint,
                  le.status,
                  le.config,
                  count(ed.id)::int as devices
                from asterisk.logical_extensions le
                join asterisk.dial_contexts dc on dc.id = le.dial_context_id
                left join asterisk.extension_devices ed on ed.logical_extension_id = le.id
                where le.tenant_id = %(tenant_id)s
                group by le.id, dc.context_key, le.logical_extension, le.display_name, le.extension_type, le.provider_endpoint, le.status, le.config
                order by dc.context_key asc, le.logical_extension asc;
                """,
                {"tenant_id": tenant_id, "tenant_key": profile["tenant_key"]},
            )
            extension_options = [
                {
                    "value": str(row["id"]),
                    "label": f"{row['logical_extension']} - {row['display_name']}",
                }
                for row in extensions
            ]
            extension_devices = fetch_records(
                cursor,
                """
                select
                  ed.id::text,
                  ed.logical_extension_id::text as extension_id,
                  le.logical_extension,
                  le.display_name as extension_name,
                  ed.device_key,
                  ed.display_name,
                  ed.device_type,
                  ed.provider_endpoint,
                  ed.registration_mode,
                  ed.status,
                  ed.config
                from asterisk.extension_devices ed
                join asterisk.logical_extensions le on le.id = ed.logical_extension_id
                where ed.tenant_id = %(tenant_id)s
                order by le.logical_extension asc, ed.device_key asc;
                """,
                tenant_id,
            )
            queues = fetch_records(
                cursor,
                """
                select
                  lq.id::text,
                  dc.context_key,
                  lq.queue_key,
                  lq.display_name,
                  lq.provider_queue_name,
                  lq.strategy,
                  lq.timeout_seconds,
                  lq.recording_required,
                  lq.status,
                  lq.config,
                  count(lqm.id)::int as members
                from asterisk.logical_queues lq
                join asterisk.dial_contexts dc on dc.id = lq.dial_context_id
                left join asterisk.logical_queue_members lqm on lqm.logical_queue_id = lq.id
                where lq.tenant_id = %(tenant_id)s
                group by lq.id, dc.context_key, lq.queue_key, lq.display_name, lq.provider_queue_name, lq.strategy, lq.timeout_seconds, lq.recording_required, lq.status, lq.config
                order by lq.queue_key asc;
                """,
                {"tenant_id": tenant_id, "tenant_key": profile["tenant_key"]},
            )
            channel_options = fetch_records(
                cursor,
                """
                select id::text as value, display_name || ' (' || channel_type || ')' as label
                from public.tenant_channels
                where tenant_id = %(tenant_id)s
                order by display_name asc, id asc;
                """,
                tenant_id,
            )
            number_options = fetch_records(
                cursor,
                """
                select id::text as value, number_e164 || ' - ' || label as label
                from public.voice_numbers
                where tenant_id = %(tenant_id)s
                order by number_e164 asc, id asc;
                """,
                tenant_id,
            )
            queue_options = [
                {"value": str(row["queue_key"]), "label": f"{row['queue_key']} - {row['display_name']}"}
                for row in queues
            ]
            context_id_options = fetch_records(
                cursor,
                """
                select id::text as value, context_key || ' - ' || display_name as label
                from asterisk.dial_contexts
                where tenant_id = %(tenant_id)s
                order by context_key asc;
                """,
                tenant_id,
            )
            context_target_options = [
                {"value": str(row["context_key"]), "label": f"{row['context_key']} - {row['display_name']}"}
                for row in contexts
            ]
            extension_target_options = [
                {"value": str(row["logical_extension"]), "label": f"{row['logical_extension']} - {row['display_name']}"}
                for row in extensions
            ]
            route_target_options = (
                [{"value": option["value"], "label": f"Queue: {option['label']}"} for option in queue_options]
                + [{"value": option["value"], "label": f"Extension: {option['label']}"} for option in extension_target_options]
                + [{"value": option["value"], "label": f"Context: {option['label']}"} for option in context_target_options]
                + [{"value": "default", "label": "Default voicemail"}, {"value": "hangup", "label": "Hang up"}]
            )
            queue_members = fetch_records(
                cursor,
                """
                select
                  lqm.id::text,
                  lq.queue_key,
                  lq.display_name as queue_name,
                  le.id::text as extension_id,
                  le.logical_extension,
                  le.display_name as extension_name,
                  lqm.penalty,
                  lqm.status
                from asterisk.logical_queue_members lqm
                join asterisk.logical_queues lq on lq.id = lqm.logical_queue_id
                join asterisk.logical_extensions le on le.id = lqm.logical_extension_id
                where lqm.tenant_id = %(tenant_id)s
                order by lq.queue_key asc, le.logical_extension asc;
                """,
                tenant_id,
            )
            routes = fetch_records(
                cursor,
                """
                select
                  rr.id::text,
                  rr.channel_id::text,
                  coalesce(tc.display_name, '') as channel,
                  rr.number_id::text,
                  coalesce(vn.number_e164, '') as number,
                  rr.inbound_context_id::text,
                  coalesce(dc.context_key, '') as inbound_context,
                  rr.target_type,
                  rr.target_id,
                  case
                    when rr.target_type = 'queue' then coalesce(lq.display_name, rr.target_id)
                    when rr.target_type = 'extension' then coalesce(le.display_name, rr.target_id)
                    when rr.target_type = 'context' then coalesce(tdc.display_name, rr.target_id)
                    else rr.target_id
                  end as target_label,
                  rr.priority,
                  rr.recording_required,
                  rr.status,
                  rr.config
                from asterisk.routing_rules rr
                left join public.tenant_channels tc on tc.id = rr.channel_id and tc.tenant_id = rr.tenant_id
                left join public.voice_numbers vn on vn.id = rr.number_id and vn.tenant_id = rr.tenant_id
                left join asterisk.dial_contexts dc on dc.id = rr.inbound_context_id and dc.tenant_id = rr.tenant_id
                left join asterisk.logical_queues lq on lq.tenant_id = rr.tenant_id and lq.queue_key = rr.target_id and rr.target_type = 'queue'
                left join asterisk.logical_extensions le on le.tenant_id = rr.tenant_id and le.logical_extension = rr.target_id and rr.target_type = 'extension'
                left join asterisk.dial_contexts tdc on tdc.tenant_id = rr.tenant_id and tdc.context_key = rr.target_id and rr.target_type = 'context'
                where rr.tenant_id = %(tenant_id)s
                order by rr.priority asc, rr.id asc;
                """,
                tenant_id,
            )
            recording = fetch_records(
                cursor,
                """
                select policy_key, display_name, scope_type, scope_id, recording_required, disclosure_required, retention_days, status
                from asterisk.recording_policies
                where tenant_id = %(tenant_id)s
                order by policy_key asc;
                """,
                tenant_id,
            )
            provisioning = fetch_records(
                cursor,
                """
                select job_type, status, requested_at::text, started_at::text, finished_at::text, error_message
                from asterisk.provisioning_jobs
                where tenant_id = %(tenant_id)s
                order by requested_at desc
                limit 25;
                """,
                tenant_id,
            )
            revisions = fetch_records(
                cursor,
                """
                select revision_key, status, config_hash, applied_at::text, created_at::text
                from asterisk.config_revisions
                where tenant_id = %(tenant_id)s
                order by created_at desc
                limit 25;
                """,
                tenant_id,
            )
            mappings = fetch_records(
                cursor,
                """
                select mapping_type, provider_object_id, provider_label, internal_object_type, internal_object_id, status
                from asterisk.provider_mappings
                where tenant_id = %(tenant_id)s
                order by mapping_type asc, provider_object_id asc;
                """,
                tenant_id,
            )
            drift = fetch_records(
                cursor,
                """
                select status, expected_hash, observed_hash, checked_at::text, created_at::text
                from asterisk.drift_checks
                where tenant_id = %(tenant_id)s
                order by created_at desc
                limit 25;
                """,
                tenant_id,
            )
            runtime = fetch_records(
                cursor,
                """
                select instance_key, status, asterisk_version, endpoint, last_seen_at::text
                from asterisk.instance_status
                order by instance_key asc;
                """,
                tenant_id,
            )

    sections = [
        {"id": "overview", "label": "Overview", "description": "Asterisk voice profile and provisioning state for this tenant. Voice numbers are managed from the tenant workspace and selected here only inside routing rules.", "status": "live", "component": "record-table", "records": [dict(profile)]},
        {"id": "contexts", "label": "Contexts", "description": "Tenant dialplan namespaces where logical extensions can repeat safely. Open Flows or Flow Steps from a context row.", "status": "live", "component": "record-table", "records": contexts},
        {
            "id": "flows",
            "label": "Flows",
            "description": "Declarative flows attached to tenant contexts before rendering Asterisk dialplan.",
            "status": "live",
            "component": "crud-resource",
            "hiddenFromTabs": True,
            "parentSectionId": "contexts",
            "crud": {
                "title": "Flows",
                "eyebrow": "flow",
                "createLabel": "Create flow",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/flows",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/flows",
                "identityField": "id",
                "titleField": "display_name",
                "searchPlaceholder": "Search flow, context or entry extension",
                "emptyTitle": "No flows match the current filters",
                "emptyDescription": "Create a flow for the selected context.",
                "allowedActions": ["view", "edit", "delete"],
                "columns": [
                    {"id": "flow_key", "header": "Flow key"},
                    {"id": "display_name", "header": "Name"},
                    {"id": "entry_extension", "header": "Entry"},
                    {"id": "steps", "header": "Steps"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"name": "context_key", "label": "Context", "control": "select", "options": context_options},
                    {"name": "flow_key", "label": "Flow key", "helperText": "Unique inside this context and version."},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "entry_extension", "label": "Entry extension", "defaultValue": "s"},
                    {"name": "version", "label": "Version", "type": "number", "defaultValue": "1"},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "draft", "label": "Draft"}, {"value": "inactive", "label": "Inactive"}]},
                    {"name": "metadata", "label": "Metadata JSON", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "context_key", "label": "Context", "control": "select", "options": context_options},
                    {"name": "flow_key", "label": "Flow key"},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "entry_extension", "label": "Entry extension"},
                    {"name": "version", "label": "Version", "type": "number"},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "draft", "label": "Draft"}, {"value": "inactive", "label": "Inactive"}]},
                    {"name": "metadata", "label": "Metadata JSON", "control": "json", "required": False},
                ],
            },
            "records": flows,
        },
        {
            "id": "flow-steps",
            "label": "Flow Steps",
            "description": "Ordered actions inside each declarative dialplan flow.",
            "status": "live",
            "component": "crud-resource",
            "hiddenFromTabs": True,
            "parentSectionId": "flows",
            "crud": {
                "title": "Flow Steps",
                "eyebrow": "step",
                "createLabel": "Create step",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/flow-steps",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/flow-steps",
                "identityField": "id",
                "titleField": "label",
                "searchPlaceholder": "Search step, action or flow",
                "emptyTitle": "No flow steps match the current filters",
                "emptyDescription": "Create ordered steps for the selected flow.",
                "allowedActions": ["view", "edit", "delete"],
                "columns": [
                    {"id": "context_key", "header": "Context"},
                    {"id": "flow_key", "header": "Flow"},
                    {"id": "step_order", "header": "Order"},
                    {"id": "action_key", "header": "Action"},
                    {"id": "label", "header": "Label"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"name": "flow_id", "label": "Flow", "control": "select", "options": flow_options},
                    {"name": "step_order", "label": "Step order", "type": "number"},
                    {"name": "action_key", "label": "Action", "control": "select", "options": action_options},
                    {"name": "label", "label": "Label"},
                    {"name": "parameters", "label": "Parameters JSON", "control": "json", "required": False, "defaultValue": "{}"},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "draft", "label": "Draft"}, {"value": "inactive", "label": "Inactive"}]},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "flow_id", "label": "Flow", "control": "select", "options": flow_options},
                    {"name": "step_order", "label": "Step order", "type": "number"},
                    {"name": "action_key", "label": "Action", "control": "select", "options": action_options},
                    {"name": "label", "label": "Label"},
                    {"name": "parameters", "label": "Parameters JSON", "control": "json", "required": False},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "draft", "label": "Draft"}, {"value": "inactive", "label": "Inactive"}]},
                ],
            },
            "records": flow_steps,
        },
        {
            "id": "extensions",
            "label": "Extensions",
            "description": "Logical extensions mapped to unique provider endpoints.",
            "status": "live",
            "component": "crud-resource",
            "crud": {
                "title": "Extensions",
                "eyebrow": "extension",
                "createLabel": "Create extension",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/extensions",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/extensions",
                "identityField": "id",
                "titleField": "logical_extension",
                "searchPlaceholder": "Search extension, endpoint, type or context",
                "emptyTitle": "No extensions match the current filters",
                "emptyDescription": "Create logical extensions for this tenant.",
                "allowedActions": ["view", "edit", "delete"],
                "columns": [
                    {"id": "context_key", "header": "Context"},
                    {"id": "logical_extension", "header": "Extension"},
                    {"id": "display_name", "header": "Name"},
                    {"id": "extension_type", "header": "Type"},
                    {"id": "provider_endpoint", "header": "Endpoint"},
                    {"id": "devices", "header": "Devices"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"name": "context_key", "label": "Context", "control": "select", "options": context_options, "defaultValue": "internal"},
                    {"name": "logical_extension", "label": "Logical extension", "helperText": "Tenant-local extension. The same number may exist in another tenant/context."},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "extension_type", "label": "Type", "control": "select", "options": [{"value": "agent", "label": "Agent"}, {"value": "supervisor", "label": "Supervisor"}, {"value": "tenant_contact", "label": "Tenant contact"}, {"value": "test", "label": "Test"}, {"value": "system", "label": "System"}]},
                    {"name": "provider_endpoint", "label": "Provider endpoint", "helperText": "Unique provider-side endpoint key generated or reserved for Asterisk."},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "inactive", "label": "Inactive"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "context_key", "label": "Context", "control": "select", "options": context_options},
                    {"name": "logical_extension", "label": "Logical extension"},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "extension_type", "label": "Type", "control": "select", "options": [{"value": "agent", "label": "Agent"}, {"value": "supervisor", "label": "Supervisor"}, {"value": "tenant_contact", "label": "Tenant contact"}, {"value": "test", "label": "Test"}, {"value": "system", "label": "System"}]},
                    {"name": "provider_endpoint", "label": "Provider endpoint"},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "inactive", "label": "Inactive"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False},
                ],
            },
            "records": extensions,
        },
        {
            "id": "extension-devices",
            "label": "Extension Devices",
            "description": "Concrete devices and endpoints where the selected logical extension can ring or register.",
            "status": "live",
            "component": "crud-resource",
            "hiddenFromTabs": True,
            "parentSectionId": "extensions",
            "crud": {
                "title": "Extension Devices",
                "eyebrow": "device",
                "createLabel": "Add device",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/extension-devices",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/extension-devices",
                "identityField": "id",
                "titleField": "device_key",
                "searchPlaceholder": "Search device, extension, endpoint or type",
                "emptyTitle": "No devices match the current filters",
                "emptyDescription": "Add web phones, SIP phones, softphones or forwards for this extension.",
                "allowedActions": ["view", "edit", "delete"],
                "columns": [
                    {"id": "device_key", "header": "Device key"},
                    {"id": "display_name", "header": "Name"},
                    {"id": "device_type", "header": "Type"},
                    {"id": "registration_mode", "header": "Registration"},
                    {"id": "status", "header": "Status"},
                ],
                "filters": [
                    {"key": "device_type", "label": "Type", "allLabel": "All types", "options": [{"value": "web_phone", "label": "Web phone"}, {"value": "sip_phone", "label": "SIP phone"}, {"value": "mobile_softphone", "label": "Mobile softphone"}, {"value": "desktop_softphone", "label": "Desktop softphone"}, {"value": "external_forward", "label": "External forward"}]},
                    {"key": "registration_mode", "label": "Registration", "allLabel": "All registration modes", "options": [{"value": "managed_app", "label": "Managed app"}, {"value": "generated_credentials", "label": "Generated credentials"}, {"value": "manual_credentials", "label": "Manual credentials"}, {"value": "external_number", "label": "External number"}]},
                ],
                "createFields": [
                    {"name": "extension_id", "label": "Extension", "control": "select", "options": extension_options},
                    {"name": "device_key", "label": "Device key", "helperText": "Unique inside this extension, such as web-pc or sip-desk."},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "device_type", "label": "Type", "control": "select", "options": [{"value": "web_phone", "label": "Web phone"}, {"value": "sip_phone", "label": "SIP phone"}, {"value": "mobile_softphone", "label": "Mobile softphone"}, {"value": "desktop_softphone", "label": "Desktop softphone"}, {"value": "external_forward", "label": "External forward"}]},
                    {"name": "provider_endpoint", "label": "Provider endpoint", "helperText": "Unique endpoint key reserved for provisioning; do not put SIP passwords here."},
                    {"name": "registration_mode", "label": "Registration mode", "control": "select", "options": [{"value": "managed_app", "label": "Managed app"}, {"value": "generated_credentials", "label": "Generated credentials"}, {"value": "manual_credentials", "label": "Manual credentials"}, {"value": "external_number", "label": "External number"}]},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "inactive", "label": "Inactive"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "extension_id", "label": "Extension", "control": "select", "options": extension_options},
                    {"name": "device_key", "label": "Device key"},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "device_type", "label": "Type", "control": "select", "options": [{"value": "web_phone", "label": "Web phone"}, {"value": "sip_phone", "label": "SIP phone"}, {"value": "mobile_softphone", "label": "Mobile softphone"}, {"value": "desktop_softphone", "label": "Desktop softphone"}, {"value": "external_forward", "label": "External forward"}]},
                    {"name": "provider_endpoint", "label": "Provider endpoint"},
                    {"name": "registration_mode", "label": "Registration mode", "control": "select", "options": [{"value": "managed_app", "label": "Managed app"}, {"value": "generated_credentials", "label": "Generated credentials"}, {"value": "manual_credentials", "label": "Manual credentials"}, {"value": "external_number", "label": "External number"}]},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "inactive", "label": "Inactive"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False},
                ],
            },
            "records": extension_devices,
        },
        {
            "id": "queues",
            "label": "Queues",
            "description": "Managed reception queues for this tenant. Open Members from a queue row.",
            "status": "live",
            "component": "crud-resource",
            "crud": {
                "title": "Queues",
                "eyebrow": "queue",
                "createLabel": "Create queue",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/queues",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/queues",
                "identityField": "id",
                "titleField": "queue_key",
                "searchPlaceholder": "Search queue, context, strategy or provider name",
                "emptyTitle": "No queues match the current filters",
                "emptyDescription": "Create tenant queues for managed reception and routing.",
                "allowedActions": ["view", "edit", "delete"],
                "columns": [
                    {"id": "context_key", "header": "Context"},
                    {"id": "queue_key", "header": "Queue key"},
                    {"id": "display_name", "header": "Name"},
                    {"id": "strategy", "header": "Strategy"},
                    {"id": "timeout_seconds", "header": "Timeout"},
                    {"id": "members", "header": "Members"},
                    {"id": "status", "header": "Status"},
                ],
                "filters": [
                    {"key": "context_key", "label": "Context", "allLabel": "All contexts", "options": context_options},
                    {"key": "strategy", "label": "Strategy", "allLabel": "All strategies", "options": [{"value": "ringall", "label": "Ring all"}, {"value": "leastrecent", "label": "Least recent"}, {"value": "fewestcalls", "label": "Fewest calls"}, {"value": "random", "label": "Random"}, {"value": "rrmemory", "label": "Round robin"}, {"value": "linear", "label": "Linear"}]},
                ],
                "createFields": [
                    {"name": "context_key", "label": "Context", "control": "select", "options": context_options, "defaultValue": "queue"},
                    {"name": "queue_key", "label": "Queue key", "helperText": "Tenant-local functional queue key, such as front-desk or reservations."},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "provider_queue_name", "label": "Provider queue name", "helperText": "Unique provider-side queue key generated or reserved for Asterisk."},
                    {"name": "strategy", "label": "Strategy", "control": "select", "options": [{"value": "ringall", "label": "Ring all"}, {"value": "leastrecent", "label": "Least recent"}, {"value": "fewestcalls", "label": "Fewest calls"}, {"value": "random", "label": "Random"}, {"value": "rrmemory", "label": "Round robin"}, {"value": "linear", "label": "Linear"}]},
                    {"name": "timeout_seconds", "label": "Timeout seconds", "type": "number", "defaultValue": "30"},
                    {"name": "recording_required", "label": "Recording required", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}], "defaultValue": "true"},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "inactive", "label": "Inactive"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "context_key", "label": "Context", "control": "select", "options": context_options},
                    {"name": "queue_key", "label": "Queue key"},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "provider_queue_name", "label": "Provider queue name"},
                    {"name": "strategy", "label": "Strategy", "control": "select", "options": [{"value": "ringall", "label": "Ring all"}, {"value": "leastrecent", "label": "Least recent"}, {"value": "fewestcalls", "label": "Fewest calls"}, {"value": "random", "label": "Random"}, {"value": "rrmemory", "label": "Round robin"}, {"value": "linear", "label": "Linear"}]},
                    {"name": "timeout_seconds", "label": "Timeout seconds", "type": "number"},
                    {"name": "recording_required", "label": "Recording required", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}]},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "inactive", "label": "Inactive"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False},
                ],
            },
            "records": queues,
        },
        {
            "id": "queue-members",
            "label": "Queue Members",
            "description": "Extension membership inside the selected tenant queue.",
            "status": "live",
            "component": "crud-resource",
            "hiddenFromTabs": True,
            "parentSectionId": "queues",
            "crud": {
                "title": "Queue Members",
                "eyebrow": "member",
                "createLabel": "Add member",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/queue-members",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/queue-members",
                "identityField": "id",
                "titleField": "logical_extension",
                "searchPlaceholder": "Search queue member, extension or queue",
                "emptyTitle": "No members match the current filters",
                "emptyDescription": "Add tenant extensions to the selected queue.",
                "allowedActions": ["view", "edit", "delete"],
                "columns": [
                    {"id": "logical_extension", "header": "Extension"},
                    {"id": "extension_name", "header": "Name"},
                    {"id": "penalty", "header": "Penalty"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"name": "queue_key", "label": "Queue", "control": "select", "options": queue_options},
                    {"name": "extension_id", "label": "Extension", "control": "select", "options": extension_options},
                    {"name": "penalty", "label": "Penalty", "type": "number", "defaultValue": "0", "helperText": "Lower penalty members are preferred first by Asterisk queue strategy."},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "paused", "label": "Paused"}, {"value": "inactive", "label": "Inactive"}]},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "queue_key", "label": "Queue", "control": "select", "options": queue_options},
                    {"name": "extension_id", "label": "Extension", "control": "select", "options": extension_options},
                    {"name": "penalty", "label": "Penalty", "type": "number"},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "paused", "label": "Paused"}, {"value": "inactive", "label": "Inactive"}]},
                ],
            },
            "records": queue_members,
        },
        {
            "id": "routing",
            "label": "Routing",
            "description": "DID, channel and after-hours routing intent for this tenant.",
            "status": "empty" if not routes else "live",
            "component": "crud-resource",
            "crud": {
                "title": "Routing",
                "eyebrow": "route",
                "createLabel": "Create route",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/routing",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/routing",
                "identityField": "id",
                "titleField": "target_label",
                "searchPlaceholder": "Search route, channel, number, context or target",
                "emptyTitle": "No routes match the current filters",
                "emptyDescription": "Create routing rules that connect tenant channels and numbers to Asterisk contexts, queues or extensions.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "target_type", "label": "Target", "allLabel": "All targets", "options": [{"value": "queue", "label": "Queue"}, {"value": "extension", "label": "Extension"}, {"value": "context", "label": "Context"}, {"value": "external_number", "label": "External number"}, {"value": "voicemail", "label": "Voicemail"}, {"value": "hangup", "label": "Hangup"}]},
                    {"key": "status", "label": "Status", "allLabel": "All statuses", "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "failed", "label": "Failed"}]},
                ],
                "columns": [
                    {"id": "priority", "header": "Priority"},
                    {"id": "channel", "header": "Channel"},
                    {"id": "number", "header": "Number"},
                    {"id": "inbound_context", "header": "Context"},
                    {"id": "target_type", "header": "Target type"},
                    {"id": "target_label", "header": "Target"},
                    {"id": "recording_required", "header": "Recording"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"name": "channel_id", "label": "Channel", "control": "select", "options": [{"value": "", "label": "Any channel"}] + channel_options, "required": False},
                    {"name": "number_id", "label": "Number", "control": "select", "options": [{"value": "", "label": "Any number"}] + number_options, "required": False},
                    {"name": "inbound_context_id", "label": "Inbound context", "control": "select", "options": [{"value": "", "label": "Default inbound context"}] + context_id_options, "required": False},
                    {"name": "target_type", "label": "Target type", "control": "select", "options": [{"value": "queue", "label": "Queue"}, {"value": "extension", "label": "Extension"}, {"value": "context", "label": "Context"}, {"value": "external_number", "label": "External number"}, {"value": "voicemail", "label": "Voicemail"}, {"value": "hangup", "label": "Hangup"}], "defaultValue": "queue"},
                    {"name": "target_id", "label": "Target", "control": "select", "options": route_target_options, "helperText": "Select a target compatible with the target type. External numbers can be edited after creation if needed."},
                    {"name": "priority", "label": "Priority", "type": "number", "defaultValue": "100"},
                    {"name": "recording_required", "label": "Recording required", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}], "defaultValue": "true"},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "failed", "label": "Failed"}], "defaultValue": "active"},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "channel_id", "label": "Channel", "control": "select", "options": [{"value": "", "label": "Any channel"}] + channel_options, "required": False},
                    {"name": "number_id", "label": "Number", "control": "select", "options": [{"value": "", "label": "Any number"}] + number_options, "required": False},
                    {"name": "inbound_context_id", "label": "Inbound context", "control": "select", "options": [{"value": "", "label": "Default inbound context"}] + context_id_options, "required": False},
                    {"name": "target_type", "label": "Target type", "control": "select", "options": [{"value": "queue", "label": "Queue"}, {"value": "extension", "label": "Extension"}, {"value": "context", "label": "Context"}, {"value": "external_number", "label": "External number"}, {"value": "voicemail", "label": "Voicemail"}, {"value": "hangup", "label": "Hangup"}]},
                    {"name": "target_id", "label": "Target", "helperText": "For queues use queue_key; for extensions use logical_extension; for contexts use context_key."},
                    {"name": "priority", "label": "Priority", "type": "number"},
                    {"name": "recording_required", "label": "Recording required", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}]},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False},
                ],
            },
            "records": routes,
        },
        {"id": "recording", "label": "Recording", "description": "Recording policy intent applied by the Asterisk provisioner.", "status": "empty" if not recording else "live", "component": "record-table", "records": recording},
        {"id": "provisioning", "label": "Provisioning", "description": "Render, apply, reload and rollback jobs.", "status": "technical-view", "component": "record-table", "records": provisioning},
        {"id": "revisions", "label": "Revisions", "description": "Generated configuration revisions and applied hashes.", "status": "technical-view", "component": "record-table", "records": revisions},
        {"id": "mappings", "label": "Mappings", "description": "Provider object mappings for contexts, queues, endpoints and recording paths.", "status": "technical-view", "component": "record-table", "records": mappings},
        {"id": "drift", "label": "Drift", "description": "Desired versus applied Asterisk state checks.", "status": "technical-view", "component": "record-table", "records": drift},
        {"id": "runtime", "label": "Runtime", "description": "Asterisk instance health and adapter diagnostics.", "status": "technical-view", "component": "record-table", "records": runtime},
    ]

    return {
        "workspace": {"id": "settings.asterisk.tenant", "title": "Asterisk Tenant Workspace", "status": "Live"},
        "subject": {
            "id": profile["id_text"],
            "key": profile["tenant_key"],
            "title": profile["display_name"],
            "subtitle": f"{profile['namespace_key']} · context prefix {profile['default_context_prefix']}",
            "status": profile["voice_status"],
            "badges": [profile["provisioning_mode"], profile["timezone"]],
        },
        "context": {"client_id": profile["tenant_key"], "role": "system_admin"},
        "links": {},
        "actions": [],
        "summary": [
            {"label": "Contexts", "value": counts["contexts"], "tone": "green"},
            {"label": "Extensions", "value": counts["extensions"], "tone": "amber"},
            {"label": "Queues", "value": counts["queues"], "tone": "blue"},
            {"label": "Flows", "value": counts["flows"], "tone": "green"},
            {"label": "Steps", "value": counts["steps"], "tone": "blue"},
            {"label": "Routes", "value": counts["routes"], "tone": "green"},
            {"label": "Recording", "value": counts["recording_policies"], "tone": "amber"},
            {"label": "Jobs", "value": counts["pending_jobs"], "tone": "red"},
            {"label": "Drift", "value": counts["drift_alerts"], "tone": "red"},
        ],
        "sections": sections,
    }


@app.post("/api/v1/asterisk/tenants/{tenant_key}/flows", status_code=status.HTTP_201_CREATED)
def create_flow(tenant_key: str, payload: DialplanFlowPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            context_id = context_id_for_key(cursor, tenant_id, payload.context_key)
            cursor.execute(
                """
                insert into asterisk.dialplan_flows (
                  tenant_id, dial_context_id, flow_key, display_name, entry_extension, status, version, metadata
                )
                values (
                  %(tenant_id)s, %(dial_context_id)s, %(flow_key)s, %(display_name)s,
                  %(entry_extension)s, %(status)s, %(version)s, %(metadata)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "dial_context_id": context_id,
                    "flow_key": payload.flow_key,
                    "display_name": payload.display_name,
                    "entry_extension": payload.entry_extension,
                    "status": payload.status,
                    "version": payload.version,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/flows/{flow_id}")
def update_flow(tenant_key: str, flow_id: int, payload: DialplanFlowPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            context_id = context_id_for_key(cursor, tenant_id, payload.context_key)
            cursor.execute(
                """
                update asterisk.dialplan_flows
                set
                  dial_context_id = %(dial_context_id)s,
                  flow_key = %(flow_key)s,
                  display_name = %(display_name)s,
                  entry_extension = %(entry_extension)s,
                  status = %(status)s,
                  version = %(version)s,
                  metadata = %(metadata)s::jsonb
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": flow_id,
                    "tenant_id": tenant_id,
                    "dial_context_id": context_id,
                    "flow_key": payload.flow_key,
                    "display_name": payload.display_name,
                    "entry_extension": payload.entry_extension,
                    "status": payload.status,
                    "version": payload.version,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialplan flow not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/flows/{flow_id}")
def delete_flow(tenant_key: str, flow_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.dialplan_flows
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": flow_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialplan flow not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.post("/api/v1/asterisk/tenants/{tenant_key}/flow-steps", status_code=status.HTTP_201_CREATED)
def create_flow_step(tenant_key: str, payload: DialplanStepPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            flow_id = ensure_flow_id(cursor, tenant_id, payload.flow_id)
            cursor.execute(
                """
                insert into asterisk.dialplan_steps (
                  tenant_id, dialplan_flow_id, step_order, action_key, label, parameters, status
                )
                values (
                  %(tenant_id)s, %(dialplan_flow_id)s, %(step_order)s, %(action_key)s,
                  %(label)s, %(parameters)s::jsonb, %(status)s
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "dialplan_flow_id": flow_id,
                    "step_order": payload.step_order,
                    "action_key": payload.action_key,
                    "label": payload.label,
                    "parameters": json.dumps(payload.parameters),
                    "status": payload.status,
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/flow-steps/{step_id}")
def update_flow_step(tenant_key: str, step_id: int, payload: DialplanStepPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            flow_id = ensure_flow_id(cursor, tenant_id, payload.flow_id)
            cursor.execute(
                """
                update asterisk.dialplan_steps
                set
                  dialplan_flow_id = %(dialplan_flow_id)s,
                  step_order = %(step_order)s,
                  action_key = %(action_key)s,
                  label = %(label)s,
                  parameters = %(parameters)s::jsonb,
                  status = %(status)s
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": step_id,
                    "tenant_id": tenant_id,
                    "dialplan_flow_id": flow_id,
                    "step_order": payload.step_order,
                    "action_key": payload.action_key,
                    "label": payload.label,
                    "parameters": json.dumps(payload.parameters),
                    "status": payload.status,
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialplan step not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/flow-steps/{step_id}")
def delete_flow_step(tenant_key: str, step_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.dialplan_steps
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": step_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dialplan step not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.post("/api/v1/asterisk/tenants/{tenant_key}/extensions", status_code=status.HTTP_201_CREATED)
def create_extension(tenant_key: str, payload: LogicalExtensionPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            context_id = context_id_for_key(cursor, tenant_id, payload.context_key)
            cursor.execute(
                """
                insert into asterisk.logical_extensions (
                  tenant_id, dial_context_id, logical_extension, display_name,
                  extension_type, provider_endpoint, status, config
                )
                values (
                  %(tenant_id)s, %(dial_context_id)s, %(logical_extension)s, %(display_name)s,
                  %(extension_type)s, %(provider_endpoint)s, %(status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "dial_context_id": context_id,
                    "logical_extension": payload.logical_extension,
                    "display_name": payload.display_name,
                    "extension_type": payload.extension_type,
                    "provider_endpoint": payload.provider_endpoint,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/extensions/{extension_id}")
def update_extension(tenant_key: str, extension_id: int, payload: LogicalExtensionPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            context_id = context_id_for_key(cursor, tenant_id, payload.context_key)
            cursor.execute(
                """
                update asterisk.logical_extensions
                set
                  dial_context_id = %(dial_context_id)s,
                  logical_extension = %(logical_extension)s,
                  display_name = %(display_name)s,
                  extension_type = %(extension_type)s,
                  provider_endpoint = %(provider_endpoint)s,
                  status = %(status)s,
                  config = %(config)s::jsonb
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": extension_id,
                    "tenant_id": tenant_id,
                    "dial_context_id": context_id,
                    "logical_extension": payload.logical_extension,
                    "display_name": payload.display_name,
                    "extension_type": payload.extension_type,
                    "provider_endpoint": payload.provider_endpoint,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logical extension not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/extensions/{extension_id}")
def delete_extension(tenant_key: str, extension_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.logical_extensions
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": extension_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logical extension not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.post("/api/v1/asterisk/tenants/{tenant_key}/extension-devices", status_code=status.HTTP_201_CREATED)
def create_extension_device(tenant_key: str, payload: ExtensionDevicePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            extension_id = ensure_extension_id(cursor, tenant_id, payload.extension_id)
            cursor.execute(
                """
                insert into asterisk.extension_devices (
                  tenant_id, logical_extension_id, device_key, display_name,
                  device_type, provider_endpoint, registration_mode, status, config
                )
                values (
                  %(tenant_id)s, %(logical_extension_id)s, %(device_key)s, %(display_name)s,
                  %(device_type)s, %(provider_endpoint)s, %(registration_mode)s, %(status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "logical_extension_id": extension_id,
                    "device_key": payload.device_key,
                    "display_name": payload.display_name,
                    "device_type": payload.device_type,
                    "provider_endpoint": payload.provider_endpoint,
                    "registration_mode": payload.registration_mode,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/extension-devices/{device_id}")
def update_extension_device(tenant_key: str, device_id: int, payload: ExtensionDevicePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            extension_id = ensure_extension_id(cursor, tenant_id, payload.extension_id)
            cursor.execute(
                """
                update asterisk.extension_devices
                set
                  logical_extension_id = %(logical_extension_id)s,
                  device_key = %(device_key)s,
                  display_name = %(display_name)s,
                  device_type = %(device_type)s,
                  provider_endpoint = %(provider_endpoint)s,
                  registration_mode = %(registration_mode)s,
                  status = %(status)s,
                  config = %(config)s::jsonb
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": device_id,
                    "tenant_id": tenant_id,
                    "logical_extension_id": extension_id,
                    "device_key": payload.device_key,
                    "display_name": payload.display_name,
                    "device_type": payload.device_type,
                    "provider_endpoint": payload.provider_endpoint,
                    "registration_mode": payload.registration_mode,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension device not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/extension-devices/{device_id}")
def delete_extension_device(tenant_key: str, device_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.extension_devices
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": device_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension device not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.post("/api/v1/asterisk/tenants/{tenant_key}/queues", status_code=status.HTTP_201_CREATED)
def create_queue(tenant_key: str, payload: LogicalQueuePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            context_id = context_id_for_key(cursor, tenant_id, payload.context_key)
            cursor.execute(
                """
                insert into asterisk.logical_queues (
                  tenant_id, dial_context_id, queue_key, display_name, provider_queue_name,
                  strategy, timeout_seconds, recording_required, status, config
                )
                values (
                  %(tenant_id)s, %(dial_context_id)s, %(queue_key)s, %(display_name)s, %(provider_queue_name)s,
                  %(strategy)s, %(timeout_seconds)s, %(recording_required)s, %(status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "dial_context_id": context_id,
                    "queue_key": payload.queue_key,
                    "display_name": payload.display_name,
                    "provider_queue_name": payload.provider_queue_name,
                    "strategy": payload.strategy,
                    "timeout_seconds": payload.timeout_seconds,
                    "recording_required": payload.recording_required,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/queues/{queue_id}")
def update_queue(tenant_key: str, queue_id: int, payload: LogicalQueuePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            context_id = context_id_for_key(cursor, tenant_id, payload.context_key)
            cursor.execute(
                """
                update asterisk.logical_queues
                set
                  dial_context_id = %(dial_context_id)s,
                  queue_key = %(queue_key)s,
                  display_name = %(display_name)s,
                  provider_queue_name = %(provider_queue_name)s,
                  strategy = %(strategy)s,
                  timeout_seconds = %(timeout_seconds)s,
                  recording_required = %(recording_required)s,
                  status = %(status)s,
                  config = %(config)s::jsonb
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": queue_id,
                    "tenant_id": tenant_id,
                    "dial_context_id": context_id,
                    "queue_key": payload.queue_key,
                    "display_name": payload.display_name,
                    "provider_queue_name": payload.provider_queue_name,
                    "strategy": payload.strategy,
                    "timeout_seconds": payload.timeout_seconds,
                    "recording_required": payload.recording_required,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logical queue not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/queues/{queue_id}")
def delete_queue(tenant_key: str, queue_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.logical_queues
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": queue_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logical queue not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.post("/api/v1/asterisk/tenants/{tenant_key}/queue-members", status_code=status.HTTP_201_CREATED)
def create_queue_member(tenant_key: str, payload: QueueMemberPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            queue_id = queue_id_for_key(cursor, tenant_id, payload.queue_key)
            extension_id = ensure_extension_id(cursor, tenant_id, payload.extension_id)
            cursor.execute(
                """
                insert into asterisk.logical_queue_members (
                  tenant_id, logical_queue_id, logical_extension_id, penalty, status
                )
                values (
                  %(tenant_id)s, %(logical_queue_id)s, %(logical_extension_id)s, %(penalty)s, %(status)s
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "logical_queue_id": queue_id,
                    "logical_extension_id": extension_id,
                    "penalty": payload.penalty,
                    "status": payload.status,
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/queue-members/{member_id}")
def update_queue_member(tenant_key: str, member_id: int, payload: QueueMemberPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            queue_id = queue_id_for_key(cursor, tenant_id, payload.queue_key)
            extension_id = ensure_extension_id(cursor, tenant_id, payload.extension_id)
            cursor.execute(
                """
                update asterisk.logical_queue_members
                set
                  logical_queue_id = %(logical_queue_id)s,
                  logical_extension_id = %(logical_extension_id)s,
                  penalty = %(penalty)s,
                  status = %(status)s
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": member_id,
                    "tenant_id": tenant_id,
                    "logical_queue_id": queue_id,
                    "logical_extension_id": extension_id,
                    "penalty": payload.penalty,
                    "status": payload.status,
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue member not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/queue-members/{member_id}")
def delete_queue_member(tenant_key: str, member_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.logical_queue_members
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": member_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue member not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}


@app.post("/api/v1/asterisk/tenants/{tenant_key}/routing", status_code=status.HTTP_201_CREATED)
def create_routing_rule(tenant_key: str, payload: RoutingRulePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            ensure_channel_id(cursor, tenant_id, payload.channel_id)
            ensure_number_id(cursor, tenant_id, payload.number_id)
            ensure_context_id(cursor, tenant_id, payload.inbound_context_id)
            ensure_route_target(cursor, tenant_id, payload.target_type, payload.target_id)
            cursor.execute(
                """
                insert into asterisk.routing_rules (
                  tenant_id, channel_id, number_id, inbound_context_id, target_type, target_id,
                  priority, recording_required, status, config
                )
                values (
                  %(tenant_id)s, %(channel_id)s, %(number_id)s, %(inbound_context_id)s, %(target_type)s, %(target_id)s,
                  %(priority)s, %(recording_required)s, %(status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "channel_id": payload.channel_id,
                    "number_id": payload.number_id,
                    "inbound_context_id": payload.inbound_context_id,
                    "target_type": payload.target_type,
                    "target_id": payload.target_id,
                    "priority": payload.priority,
                    "recording_required": payload.recording_required,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/routing/{route_id}")
def update_routing_rule(tenant_key: str, route_id: int, payload: RoutingRulePayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            ensure_channel_id(cursor, tenant_id, payload.channel_id)
            ensure_number_id(cursor, tenant_id, payload.number_id)
            ensure_context_id(cursor, tenant_id, payload.inbound_context_id)
            ensure_route_target(cursor, tenant_id, payload.target_type, payload.target_id)
            cursor.execute(
                """
                update asterisk.routing_rules
                set
                  channel_id = %(channel_id)s,
                  number_id = %(number_id)s,
                  inbound_context_id = %(inbound_context_id)s,
                  target_type = %(target_type)s,
                  target_id = %(target_id)s,
                  priority = %(priority)s,
                  recording_required = %(recording_required)s,
                  status = %(status)s,
                  config = %(config)s::jsonb
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": route_id,
                    "tenant_id": tenant_id,
                    "channel_id": payload.channel_id,
                    "number_id": payload.number_id,
                    "inbound_context_id": payload.inbound_context_id,
                    "target_type": payload.target_type,
                    "target_id": payload.target_id,
                    "priority": payload.priority,
                    "recording_required": payload.recording_required,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing rule not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/routing/{route_id}")
def delete_routing_rule(tenant_key: str, route_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.routing_rules
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": route_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing rule not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}
