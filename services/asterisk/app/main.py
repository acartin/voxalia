import json
import os
import shlex
import socket
import subprocess
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
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
    status: str = "active"
    config: dict[str, Any] = Field(default_factory=dict)


class RecordingPolicyPayload(BaseModel):
    policy_key: str = Field(min_length=1, max_length=120, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(min_length=1, max_length=160)
    scope_type: str = Field(pattern="^(tenant|channel|number|queue|extension)$")
    scope_id: str = Field(default="", max_length=240)
    recording_required: bool = True
    disclosure_required: bool = True
    retention_days: int = Field(default=365, gt=0)
    storage_path_template: str = Field(default="", max_length=500)
    status: str = Field(default="active", pattern="^(active|inactive|draft)$")
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


class ApplyConfigPayload(BaseModel):
    mode: str = Field(default="render_only", pattern="^(render_only|apply)$")


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


def _rows(cursor, query: str, params: dict[str, object] | None = None) -> list[dict[str, Any]]:
    cursor.execute(query, params or {})
    return [dict(row) for row in cursor.fetchall()]


def _safe_comment(value: object) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").strip()


def _dialplan_action_line(step: dict[str, Any], queues: dict[str, dict[str, Any]], extensions: dict[str, dict[str, Any]], contexts: dict[str, dict[str, Any]]) -> str:
    action = str(step["action_key"])
    params = step.get("parameters") if isinstance(step.get("parameters"), dict) else {}
    label = _safe_comment(step.get("label") or action)

    if action == "answer":
        return f" same => n,Answer() ; {label}"
    if action == "play_disclosure":
        script_key = _safe_comment(params.get("script_key") or "recording-disclosure")
        return f" same => n,Playback(custom/{script_key}) ; {label}"
    if action == "start_recording":
        policy_key = _safe_comment(params.get("policy_key") or "default")
        return f" same => n,MixMonitor(${{UNIQUEID}}-{policy_key}.wav,b) ; {label}"
    if action == "check_business_hours":
        open_target = _safe_comment(params.get("open_target") or "open")
        closed_target = _safe_comment(params.get("closed_target") or "closed")
        return f" same => n,NoOp(Check business hours open={open_target} closed={closed_target}) ; {label}"
    if action == "route_to_queue":
        queue_key = str(params.get("queue_key") or params.get("target") or "")
        queue = queues.get(queue_key, {})
        queue_name = _safe_comment(queue.get("provider_queue_name") or queue_key or "missing-queue")
        return f" same => n,Queue({queue_name}) ; {label}"
    if action == "route_to_extension":
        logical_extension = str(params.get("logical_extension") or params.get("target") or "")
        extension = extensions.get(logical_extension, {})
        endpoint = _safe_comment(extension.get("provider_endpoint") or logical_extension or "missing-endpoint")
        return f" same => n,Dial(PJSIP/{endpoint},30) ; {label}"
    if action == "route_to_context":
        context_key = str(params.get("context_key") or "")
        context = contexts.get(context_key, {})
        context_name = _safe_comment(context.get("provider_context_name") or context_key or "missing-context")
        entry_extension = _safe_comment(params.get("entry_extension") or "s")
        return f" same => n,Goto({context_name},{entry_extension},1) ; {label}"
    if action == "set_caller_id":
        caller_id = _safe_comment(params.get("caller_id") or "")
        return f" same => n,Set(CALLERID(num)={caller_id}) ; {label}"
    if action == "dial_external":
        destination = _safe_comment(params.get("destination") or "missing-destination")
        return f" same => n,Dial(PJSIP/{destination}@voxalia-outbound,45) ; {label}"
    if action == "take_message":
        return f" same => n,VoiceMail(default@default,u) ; {label}"
    if action == "create_task":
        task_type = _safe_comment(params.get("task_type") or "follow_up")
        return f" same => n,NoOp(Create Voxalia task type={task_type}) ; {label}"
    if action == "emit_event":
        event_type = _safe_comment(params.get("event_type") or "dialplan.event")
        return f" same => n,NoOp(Emit Voxalia event type={event_type}) ; {label}"
    if action == "hangup":
        return f" same => n,Hangup() ; {label}"
    return f" same => n,NoOp(Unsupported Voxalia action {action}) ; {label}"


def _render_tenant_files(tenant: dict[str, Any]) -> dict[str, str]:
    contexts = {str(row["context_key"]): row for row in tenant["contexts"]}
    queues = {str(row["queue_key"]): row for row in tenant["queues"]}
    extensions = {str(row["logical_extension"]): row for row in tenant["extensions"]}
    devices_by_extension: dict[str, list[dict[str, Any]]] = {}
    for device in tenant["extension_devices"]:
        devices_by_extension.setdefault(str(device["logical_extension"]), []).append(device)

    pjsip_lines = [
        f"; Generated by Voxalia for {tenant['tenant_key']}",
        "; Secrets are intentionally not rendered in this preview.",
    ]
    for extension in tenant["extensions"]:
        endpoint = _safe_comment(extension["provider_endpoint"])
        pjsip_lines.extend(
            [
                "",
                f"[{endpoint}]",
                "type=endpoint",
                "transport=transport-udp",
                "context=" + _safe_comment(extension["provider_context_name"]),
                "disallow=all",
                "allow=ulaw,alaw",
                f"; logical_extension={_safe_comment(extension['logical_extension'])}",
                f"; display_name={_safe_comment(extension['display_name'])}",
            ]
        )
        for device in devices_by_extension.get(str(extension["logical_extension"]), []):
            pjsip_lines.append(f"; device={_safe_comment(device['device_key'])} endpoint={_safe_comment(device['provider_endpoint'])} mode={_safe_comment(device['registration_mode'])}")

    queues_lines = [
        f"; Generated by Voxalia for {tenant['tenant_key']}",
    ]
    queue_members_by_key: dict[str, list[dict[str, Any]]] = {}
    for member in tenant["queue_members"]:
        queue_members_by_key.setdefault(str(member["queue_key"]), []).append(member)
    for queue in tenant["queues"]:
        queue_name = _safe_comment(queue["provider_queue_name"])
        queues_lines.extend(
            [
                "",
                f"[{queue_name}]",
                f"strategy={_safe_comment(queue['strategy'])}",
                f"timeout={int(queue['timeout_seconds'])}",
            ]
        )
        for member in queue_members_by_key.get(str(queue["queue_key"]), []):
            endpoint = _safe_comment(member["provider_endpoint"])
            penalty = int(member["penalty"])
            queues_lines.append(f"member => PJSIP/{endpoint},{penalty},{_safe_comment(member['extension_name'])}")

    extensions_lines = [
        f"; Generated by Voxalia for {tenant['tenant_key']}",
    ]
    flows_by_context: dict[str, list[dict[str, Any]]] = {}
    steps_by_flow: dict[str, list[dict[str, Any]]] = {}
    for flow in tenant["flows"]:
        flows_by_context.setdefault(str(flow["context_key"]), []).append(flow)
    for step in tenant["flow_steps"]:
        steps_by_flow.setdefault(str(step["flow_id"]), []).append(step)

    for context in tenant["contexts"]:
        context_key = str(context["context_key"])
        context_name = _safe_comment(context["provider_context_name"])
        extensions_lines.extend(["", f"[{context_name}]", f"; {context_key} - {_safe_comment(context['display_name'])}"])

        for flow in flows_by_context.get(context_key, []):
            entry_extension = _safe_comment(flow["entry_extension"])
            extensions_lines.append(f"exten => {entry_extension},1,NoOp(Voxalia flow {_safe_comment(flow['flow_key'])})")
            for step in steps_by_flow.get(str(flow["id"]), []):
                extensions_lines.append(_dialplan_action_line(step, queues, extensions, contexts))
            extensions_lines.append(" same => n,Hangup()")

        for extension in tenant["extensions"]:
            if str(extension["context_key"]) != context_key:
                continue
            logical_extension = _safe_comment(extension["logical_extension"])
            endpoint = _safe_comment(extension["provider_endpoint"])
            extensions_lines.append(f"exten => {logical_extension},1,Dial(PJSIP/{endpoint},30)")

    routing_lines = [
        f"; Routing preview for {tenant['tenant_key']}",
    ]
    for route in tenant["routes"]:
        inbound_context = _safe_comment(route.get("inbound_context") or "default-inbound")
        number = _safe_comment(route.get("number") or "any-number")
        target_type = _safe_comment(route["target_type"])
        target_id = _safe_comment(route["target_id"])
        routing_lines.append(f"; priority={route['priority']} channel={_safe_comment(route.get('channel') or 'any-channel')} number={number} context={inbound_context} target={target_type}:{target_id}")

    recording_lines = [
        f"; Recording policies for {tenant['tenant_key']}",
    ]
    for policy in tenant["recording_policies"]:
        recording_lines.append(
            f"; {policy['policy_key']} scope={policy['scope_type']}:{policy.get('scope_id') or '*'} record={policy['recording_required']} disclosure={policy['disclosure_required']} retention_days={policy['retention_days']}"
        )

    return {
        "pjsip.conf": "\n".join(pjsip_lines).strip() + "\n",
        "queues.conf": "\n".join(queues_lines).strip() + "\n",
        "extensions.conf": "\n".join(extensions_lines).strip() + "\n",
        "voxalia-routing.preview": "\n".join(routing_lines).strip() + "\n",
        "voxalia-recording.preview": "\n".join(recording_lines).strip() + "\n",
    }


def render_asterisk_config(cursor, mode: str) -> dict[str, Any]:
    infrastructure = {
        "trunks": _rows(cursor, "select trunk_key, display_name, carrier_key, provider_endpoint, transport, trunk_role, registration_mode, auth_mode, match_strategy, remote_hosts, codecs, max_channels, status, config from asterisk.sip_trunks order by trunk_key asc;"),
        "carriers": _rows(cursor, "select carrier_key, display_name, provider_name, account_scope, region, support_status, failover_policy, status, config from asterisk.carriers order by carrier_key asc;"),
        "instances": _rows(cursor, "select instance_key, display_name, environment, role, control_mode, endpoint_ref, region, asterisk_version, capabilities, status, health_status, config from asterisk.instances order by instance_key asc;"),
    }

    tenants = _rows(
        cursor,
        """
        select
          t.id as tenant_id,
          t.tenant_key,
          t.display_name,
          p.namespace_key,
          p.default_context_prefix,
          p.default_extension_prefix,
          p.provisioning_mode,
          p.status
        from asterisk.tenant_voice_profiles p
        join public.tenants t on t.id = p.tenant_id
        where p.voice_enabled = true
        order by t.display_name asc;
        """,
    )

    rendered_tenants = []
    for tenant in tenants:
        tenant_id = tenant["tenant_id"]
        tenant_payload = {key: value for key, value in tenant.items() if key != "tenant_id"}
        tenant_payload["contexts"] = _rows(
            cursor,
            "select id::text, context_key, display_name, provider_context_name, direction, status, config from asterisk.dial_contexts where tenant_id = %(tenant_id)s order by context_key asc;",
            {"tenant_id": tenant_id},
        )
        tenant_payload["flows"] = _rows(
            cursor,
            """
            select f.id::text, dc.context_key, f.flow_key, f.display_name, f.entry_extension, f.status, f.version, f.metadata
            from asterisk.dialplan_flows f
            join asterisk.dial_contexts dc on dc.id = f.dial_context_id
            where f.tenant_id = %(tenant_id)s
            order by dc.context_key asc, f.flow_key asc, f.version asc;
            """,
            {"tenant_id": tenant_id},
        )
        tenant_payload["flow_steps"] = _rows(
            cursor,
            """
            select s.id::text, s.dialplan_flow_id::text as flow_id, dc.context_key, f.flow_key, s.step_order, s.action_key, s.label, s.parameters, s.status
            from asterisk.dialplan_steps s
            join asterisk.dialplan_flows f on f.id = s.dialplan_flow_id
            join asterisk.dial_contexts dc on dc.id = f.dial_context_id
            where s.tenant_id = %(tenant_id)s
            order by dc.context_key asc, f.flow_key asc, s.step_order asc;
            """,
            {"tenant_id": tenant_id},
        )
        tenant_payload["extensions"] = _rows(
            cursor,
            """
            select le.id::text, dc.context_key, dc.provider_context_name, le.logical_extension, le.display_name, le.extension_type, le.provider_endpoint, le.status, le.config
            from asterisk.logical_extensions le
            join asterisk.dial_contexts dc on dc.id = le.dial_context_id
            where le.tenant_id = %(tenant_id)s
            order by dc.context_key asc, le.logical_extension asc;
            """,
            {"tenant_id": tenant_id},
        )
        tenant_payload["extension_devices"] = _rows(
            cursor,
            """
            select ed.id::text, le.logical_extension, ed.device_key, ed.display_name, ed.device_type, ed.provider_endpoint, ed.registration_mode, ed.status, ed.config
            from asterisk.extension_devices ed
            join asterisk.logical_extensions le on le.id = ed.logical_extension_id
            where ed.tenant_id = %(tenant_id)s
            order by le.logical_extension asc, ed.device_key asc;
            """,
            {"tenant_id": tenant_id},
        )
        tenant_payload["queues"] = _rows(
            cursor,
            """
            select lq.id::text, dc.context_key, lq.queue_key, lq.display_name, lq.provider_queue_name, lq.strategy, lq.timeout_seconds, lq.status, lq.config
            from asterisk.logical_queues lq
            join asterisk.dial_contexts dc on dc.id = lq.dial_context_id
            where lq.tenant_id = %(tenant_id)s
            order by lq.queue_key asc;
            """,
            {"tenant_id": tenant_id},
        )
        tenant_payload["queue_members"] = _rows(
            cursor,
            """
            select lq.queue_key, le.logical_extension, le.display_name as extension_name, le.provider_endpoint, lqm.penalty, lqm.status
            from asterisk.logical_queue_members lqm
            join asterisk.logical_queues lq on lq.id = lqm.logical_queue_id
            join asterisk.logical_extensions le on le.id = lqm.logical_extension_id
            where lqm.tenant_id = %(tenant_id)s
            order by lq.queue_key asc, le.logical_extension asc;
            """,
            {"tenant_id": tenant_id},
        )
        tenant_payload["channels"] = _rows(
            cursor,
            "select id::text, channel_key, channel_type, display_name, provider, routing_key, default_language, status, metadata from public.tenant_channels where tenant_id = %(tenant_id)s order by channel_key asc;",
            {"tenant_id": tenant_id},
        )
        tenant_payload["numbers"] = _rows(
            cursor,
            "select id::text, channel_id::text, number_e164, label, number_type, country_code, status, metadata from public.voice_numbers where tenant_id = %(tenant_id)s order by number_e164 asc;",
            {"tenant_id": tenant_id},
        )
        tenant_payload["routes"] = _rows(
            cursor,
            """
            select
              rr.id::text,
              coalesce(tc.display_name, '') as channel,
              coalesce(vn.number_e164, '') as number,
              coalesce(dc.context_key, '') as inbound_context,
              rr.target_type,
              rr.target_id,
              rr.priority,
              rr.status,
              rr.config
            from asterisk.routing_rules rr
            left join public.tenant_channels tc on tc.id = rr.channel_id and tc.tenant_id = rr.tenant_id
            left join public.voice_numbers vn on vn.id = rr.number_id and vn.tenant_id = rr.tenant_id
            left join asterisk.dial_contexts dc on dc.id = rr.inbound_context_id and dc.tenant_id = rr.tenant_id
            where rr.tenant_id = %(tenant_id)s
            order by rr.priority asc, rr.id asc;
            """,
            {"tenant_id": tenant_id},
        )
        tenant_payload["recording_policies"] = _rows(
            cursor,
            "select policy_key, display_name, scope_type, coalesce(scope_id, '') as scope_id, recording_required, disclosure_required, retention_days, storage_path_template, status, config from asterisk.recording_policies where tenant_id = %(tenant_id)s order by policy_key asc;",
            {"tenant_id": tenant_id},
        )
        tenant_payload["files"] = _render_tenant_files(tenant_payload)
        rendered_tenants.append(tenant_payload)

    return {
        "schema": "voxalia.asterisk.rendered-config.v1",
        "mode": mode,
        "scope": "global",
        "renderer": "services/asterisk",
        "infrastructure": infrastructure,
        "tenants": rendered_tenants,
    }


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _ami_read_line(ami_socket: socket.socket) -> str:
    data = b""
    while not data.endswith(b"\n"):
        chunk = ami_socket.recv(1)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="replace").strip()


def _ami_read_packet(ami_socket: socket.socket) -> str:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = ami_socket.recv(4096)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="replace")


def _ami_read_command_packet(ami_socket: socket.socket) -> str:
    response = _ami_read_packet(ami_socket)
    if "--END COMMAND--" not in response:
        return response

    while "\r\n\r\n" not in response.split("--END COMMAND--", 1)[1]:
        chunk = ami_socket.recv(4096)
        if not chunk:
            break
        response += chunk.decode("utf-8", errors="replace")
    return response


def _ami_send_action(ami_socket: socket.socket, action: dict[str, str], *, command: bool = False) -> str:
    payload = "".join(f"{key}: {value}\r\n" for key, value in action.items()) + "\r\n"
    ami_socket.sendall(payload.encode("utf-8"))
    return _ami_read_command_packet(ami_socket) if command else _ami_read_packet(ami_socket)


def reload_asterisk_runtime() -> dict[str, Any]:
    settings = get_settings()
    if not settings.ami_password:
        return {"status": "skipped", "reason": "VOXALIA_ASTERISK_API_AMI_PASSWORD is not configured."}

    commands = ["dialplan reload", "pjsip reload", "queue reload all"]
    responses: list[dict[str, str]] = []
    try:
        with socket.create_connection((settings.ami_host, settings.ami_port), timeout=10) as ami_socket:
            ami_socket.settimeout(15)
            greeting = _ami_read_line(ami_socket)
            login = _ami_send_action(
                ami_socket,
                {
                    "Action": "Login",
                    "Username": settings.ami_username,
                    "Secret": settings.ami_password,
                    "Events": "off",
                },
            )
            if "Response: Success" not in login:
                return {"status": "failed", "transport": "ami", "message": "AMI login failed", "greeting": greeting}

            for command in commands:
                response = _ami_send_action(ami_socket, {"Action": "Command", "Command": command}, command=True)
                responses.append({"command": command, "response": response[-1000:]})
                if "Response: Error" in response:
                    return {"status": "failed", "transport": "ami", "responses": responses}

            _ami_send_action(ami_socket, {"Action": "Logoff"})
    except OSError as exc:
        return {"status": "failed", "transport": "ami", "message": str(exc)}

    return {"status": "succeeded", "transport": "ami", "commands": commands, "responses": responses}


def check_asterisk_runtime_health() -> dict[str, Any]:
    settings = get_settings()
    if not settings.ami_password:
        return {
            "service_key": "asterisk-runtime",
            "service": "Asterisk Runtime",
            "status": "degraded",
            "detail": "AMI password is not configured.",
            "endpoint": f"{settings.ami_host}:{settings.ami_port}",
            "checked_via": "ami",
        }

    try:
        with socket.create_connection((settings.ami_host, settings.ami_port), timeout=5) as ami_socket:
            ami_socket.settimeout(5)
            greeting = _ami_read_line(ami_socket)
            login = _ami_send_action(
                ami_socket,
                {
                    "Action": "Login",
                    "Username": settings.ami_username,
                    "Secret": settings.ami_password,
                    "Events": "off",
                },
            )
            if "Response: Success" not in login:
                return {
                    "service_key": "asterisk-runtime",
                    "service": "Asterisk Runtime",
                    "status": "down",
                    "detail": "AMI login failed.",
                    "endpoint": f"{settings.ami_host}:{settings.ami_port}",
                    "checked_via": "ami",
                }

            version = _ami_send_action(ami_socket, {"Action": "Command", "Command": "core show version"}, command=True)
            _ami_send_action(ami_socket, {"Action": "Logoff"})
    except OSError as exc:
        return {
            "service_key": "asterisk-runtime",
            "service": "Asterisk Runtime",
            "status": "down",
            "detail": str(exc),
            "endpoint": f"{settings.ami_host}:{settings.ami_port}",
            "checked_via": "ami",
        }

    detail = "AMI reachable."
    for line in version.splitlines():
        if line.startswith("Output: Asterisk "):
            detail = line.replace("Output: ", "", 1)
            break

    return {
        "service_key": "asterisk-runtime",
        "service": "Asterisk Runtime",
        "status": "healthy",
        "detail": detail,
        "endpoint": f"{settings.ami_host}:{settings.ami_port}",
        "checked_via": "ami",
        "greeting": greeting,
    }


def check_rendered_file_health() -> dict[str, Any]:
    settings = get_settings()
    output_dir = Path(settings.render_output_dir)
    required_files = ["pjsip_voxalia.conf", "extensions_voxalia.conf", "queues_voxalia.conf"]
    existing_files = [file_name for file_name in required_files if (output_dir / file_name).exists()]
    missing_files = [file_name for file_name in required_files if file_name not in existing_files]
    status_value = "healthy" if not missing_files else "degraded" if existing_files else "down"
    detail = "Generated Asterisk files are present." if not missing_files else f"Missing: {', '.join(missing_files)}"

    return {
        "service_key": "rendered-config",
        "service": "Rendered Config",
        "status": status_value,
        "detail": detail,
        "endpoint": str(output_dir),
        "checked_via": "filesystem",
    }


def write_rendered_config_files(rendered_config: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    output_dir = Path(settings.render_output_dir)
    tenants = rendered_config.get("tenants") if isinstance(rendered_config.get("tenants"), list) else []
    managed_files = {
        "pjsip.conf": "pjsip_voxalia.conf",
        "extensions.conf": "extensions_voxalia.conf",
        "queues.conf": "queues_voxalia.conf",
        "voxalia-routing.preview": "voxalia-routing.preview",
        "voxalia-recording.preview": "voxalia-recording.preview",
    }
    written_files: list[str] = []

    for source_name, target_name in managed_files.items():
        parts = [
            "; Managed by Voxalia. Do not edit manually.",
            f"; schema={rendered_config.get('schema')}",
            f"; config_hash={sha256(json.dumps(rendered_config, sort_keys=True, default=str).encode('utf-8')).hexdigest()}",
            "",
        ]
        for tenant in tenants:
            if not isinstance(tenant, dict):
                continue
            files = tenant.get("files") if isinstance(tenant.get("files"), dict) else {}
            content = files.get(source_name)
            if not content:
                continue
            parts.extend(
                [
                    f"; ---- tenant={_safe_comment(tenant.get('tenant_key') or tenant.get('display_name') or 'unknown')} file={source_name} ----",
                    str(content).rstrip(),
                    "",
                ]
            )

        target_path = output_dir / target_name
        _write_atomic(target_path, "\n".join(parts).rstrip() + "\n")
        written_files.append(str(target_path))

    reload_result: dict[str, Any] = {
        "status": "skipped",
        "reason": "VOXALIA_ASTERISK_RELOAD_COMMAND is not configured for an Asterisk runtime.",
    }
    if settings.reload_command.strip():
        command = shlex.split(settings.reload_command)
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
        reload_result = {
            "status": "succeeded" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-2000:],
        }
        if completed.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"message": "Asterisk reload command failed", "reload": reload_result},
            )
    else:
        reload_result = reload_asterisk_runtime()
        if reload_result["status"] == "failed":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"message": "Asterisk runtime reload failed", "reload": reload_result},
            )

    return {
        "output_dir": str(output_dir),
        "written_files": written_files,
        "written_file_count": len(written_files),
        "reload": reload_result,
    }


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
                  (select count(*)::int from asterisk.extension_devices where status = 'active') as extension_devices,
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

            cursor.execute(
                """
                select
                  coalesce(t.display_name, 'Infrastructure') as scope,
                  coalesce(t.tenant_key, 'infrastructure') as scope_key,
                  p.job_type,
                  p.status,
                  p.requested_at::text,
                  p.started_at::text,
                  p.finished_at::text,
                  p.error_message,
                  p.result
                from asterisk.provisioning_jobs p
                left join public.tenants t on t.id = p.tenant_id
                order by p.requested_at desc
                limit 25;
                """
            )
            provisioning = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                select
                  cr.id::text,
                  cr.revision_key,
                  cr.status,
                  cr.config_hash,
                  cr.applied_at::text,
                  cr.created_at::text,
                  pj.job_type,
                  pj.status as job_status,
                  cr.rendered_config->>'schema' as schema,
                  coalesce(jsonb_array_length(cr.rendered_config->'tenants'), 0) as tenant_count,
                  (
                    select count(*)::int
                    from jsonb_array_elements(cr.rendered_config->'tenants') tenant
                    cross join jsonb_each(tenant->'files')
                  ) as rendered_files,
                  cr.rendered_config->'tenants' as rendered_tenants
                from asterisk.config_revisions cr
                left join asterisk.provisioning_jobs pj on pj.id = cr.provisioning_job_id
                order by cr.created_at desc
                limit 10;
                """
            )
            revisions = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                select
                  coalesce(t.display_name, 'Infrastructure') as scope,
                  coalesce(t.tenant_key, 'infrastructure') as scope_key,
                  d.status,
                  d.expected_hash,
                  d.observed_hash,
                  d.checked_at::text,
                  d.created_at::text
                from asterisk.drift_checks d
                left join public.tenants t on t.id = d.tenant_id
                order by d.created_at desc
                limit 25;
                """
            )
            drift = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                select instance_key, status, asterisk_version, endpoint, last_seen_at::text
                from asterisk.instance_status
                order by instance_key asc;
                """
            )
            runtime = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                select
                  'Infrastructure' as tenant,
                  'infrastructure' as tenant_key,
                  case
                    when applied.last_apply_at is null then 'pending'
                    when changed.last_config_change_at > applied.last_apply_at then 'pending'
                    else 'applied'
                  end as status,
                  'global' as profile_status,
                  'generated' as provisioning_mode,
                  changed.last_config_change_at::text,
                  pending.pending_changes,
                  coalesce(pending.pending_details, 'No pending changes') as pending_details,
                  applied.last_apply_at::text as last_provisioned_at,
                  null::text as last_drift_check_at,
                  (select count(*)::int from asterisk.provisioning_jobs where tenant_id is null and status in ('queued', 'running')) as pending_jobs,
                  (select count(*)::int from asterisk.drift_checks where tenant_id is null and status in ('drift_detected', 'failed')) as drift_alerts
                from (
                  select greatest(
                    coalesce((select max(updated_at) from asterisk.sip_trunks), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.carriers), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.instances), 'epoch'::timestamptz)
                  ) as last_config_change_at
                ) changed
                cross join (
                  select max(finished_at) as last_apply_at
                  from asterisk.provisioning_jobs
                  where tenant_id is null and job_type = 'apply_config' and status = 'succeeded'
                ) applied
                cross join lateral (
                  select
                    coalesce(sum(changes), 0)::int as pending_changes,
                    string_agg(label || ': ' || changes::text, ', ' order by sort) as pending_details
                  from (
                    values
                      (1, 'Trunks', (select count(*)::int from asterisk.sip_trunks where updated_at > coalesce(applied.last_apply_at, 'epoch'::timestamptz))),
                      (2, 'Carriers', (select count(*)::int from asterisk.carriers where updated_at > coalesce(applied.last_apply_at, 'epoch'::timestamptz))),
                      (3, 'Instances', (select count(*)::int from asterisk.instances where updated_at > coalesce(applied.last_apply_at, 'epoch'::timestamptz)))
                  ) pending_scope(sort, label, changes)
                  where changes > 0
                ) pending;
                """
            )
            infrastructure_apply_state = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                select
                  t.display_name as tenant,
                  t.tenant_key,
                  case
                    when p.status = 'failed' then 'failed'
                    when p.last_provisioned_at is null then 'pending'
                    when changed.last_config_change_at > p.last_provisioned_at then 'pending'
                    else 'applied'
                  end as status,
                  p.status as profile_status,
                  p.provisioning_mode,
                  changed.last_config_change_at::text,
                  pending.pending_changes,
                  coalesce(pending.pending_details, 'No pending changes') as pending_details,
                  p.last_provisioned_at::text,
                  p.last_drift_check_at::text,
                  (select count(*)::int from asterisk.provisioning_jobs j where j.tenant_id = p.tenant_id and j.status in ('queued', 'running')) as pending_jobs,
                  (select count(*)::int from asterisk.drift_checks d where d.tenant_id = p.tenant_id and d.status in ('drift_detected', 'failed')) as drift_alerts
                from asterisk.tenant_voice_profiles p
                join public.tenants t on t.id = p.tenant_id
                cross join lateral (
                  select greatest(
                    coalesce(p.updated_at, 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.dial_contexts where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.dialplan_flows where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(fs.updated_at) from asterisk.dialplan_steps fs join asterisk.dialplan_flows f on f.id = fs.dialplan_flow_id where fs.tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.logical_extensions where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.extension_devices where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.logical_queues where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.logical_queue_members where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.routing_rules where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from asterisk.recording_policies where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from public.voice_numbers where tenant_id = p.tenant_id), 'epoch'::timestamptz),
                    coalesce((select max(updated_at) from public.tenant_channels where tenant_id = p.tenant_id), 'epoch'::timestamptz)
                  ) as last_config_change_at
                ) changed
                cross join lateral (
                  select
                    coalesce(sum(changes), 0)::int as pending_changes,
                    string_agg(label || ': ' || changes::text, ', ' order by sort) as pending_details
                  from (
                    values
                      (1, 'Voice profile', (select count(*)::int from asterisk.tenant_voice_profiles where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (2, 'Contexts', (select count(*)::int from asterisk.dial_contexts where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (3, 'Flows', (select count(*)::int from asterisk.dialplan_flows where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (4, 'Flow steps', (select count(*)::int from asterisk.dialplan_steps where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (5, 'Extensions', (select count(*)::int from asterisk.logical_extensions where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (6, 'Extension devices', (select count(*)::int from asterisk.extension_devices where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (7, 'Queues', (select count(*)::int from asterisk.logical_queues where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (8, 'Queue members', (select count(*)::int from asterisk.logical_queue_members where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (9, 'Routing', (select count(*)::int from asterisk.routing_rules where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (10, 'Recording policies', (select count(*)::int from asterisk.recording_policies where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (11, 'Voice numbers', (select count(*)::int from public.voice_numbers where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz))),
                      (12, 'Channels', (select count(*)::int from public.tenant_channels where tenant_id = p.tenant_id and updated_at > coalesce(p.last_provisioned_at, 'epoch'::timestamptz)))
                  ) pending_scope(sort, label, changes)
                  where changes > 0
                ) pending
                order by t.display_name asc;
                """
            )
            tenant_apply_state = infrastructure_apply_state + [dict(row) for row in cursor.fetchall()]

    pending_scopes = [record for record in tenant_apply_state if str(record.get("status", "")).lower() == "pending"]
    failed_scopes = [record for record in tenant_apply_state if str(record.get("status", "")).lower() == "failed"]
    apply_health_status = "failed" if failed_scopes else "degraded" if pending_scopes else "healthy"
    apply_health_detail = (
        f"{len(failed_scopes)} failed apply scope(s)."
        if failed_scopes
        else f"{len(pending_scopes)} scope(s) have pending changes."
        if pending_scopes
        else "Current database state has been applied."
    )
    service_health = [
        {
            "service_key": "asterisk-api",
            "service": "Asterisk API",
            "status": "healthy",
            "detail": "Workspace endpoint responded and database queries completed.",
            "endpoint": "voxalia-asterisk-api:8000",
            "checked_via": "http/db",
        },
        check_asterisk_runtime_health(),
        check_rendered_file_health(),
        {
            "service_key": "apply-state",
            "service": "Apply State",
            "status": apply_health_status,
            "detail": apply_health_detail,
            "endpoint": "asterisk.provisioning_jobs",
            "checked_via": "database",
        },
        {
            "service_key": "freepbx-lab",
            "service": "FreePBX Lab",
            "status": "info",
            "detail": "Lab/reference only; not used by Voxalia Apply Config.",
            "endpoint": "freepbx",
            "checked_via": "not managed",
        },
    ]

    sections = [
        {"id": "overview", "label": "Overview", "description": "Control-plane health, active tenant namespaces and provisioning posture.", "status": "live", "component": "summary", "records": tenants},
        {"id": "service_health", "label": "Service Health", "description": "Traffic-light status for the Asterisk infrastructure services controlled by Voxalia.", "status": "live", "component": "service-health", "hiddenFromTabs": True, "records": service_health},
        {"id": "provisioning", "label": "Provisioning", "description": "Global apply status, pending jobs, drift alerts and Asterisk runtime diagnostics.", "status": "technical-view", "component": "operational-view", "records": provisioning},
        {"id": "config_revisions", "label": "Config Revisions", "description": "Rendered Asterisk configuration snapshots created by Apply Config.", "status": "technical-view", "component": "record-table", "records": revisions},
        {"id": "tenant_apply_state", "label": "Apply State", "description": "Infrastructure and per-tenant provisioning status used by the global Apply Config experience.", "status": "technical-view", "component": "record-table", "records": tenant_apply_state},
        {"id": "drift", "label": "Drift", "description": "Checks that compare desired Voxalia state with the applied Asterisk runtime state.", "status": "technical-view", "component": "record-table", "records": drift},
        {"id": "runtime", "label": "Runtime", "description": "Asterisk instance health, version, last seen timestamp and adapter diagnostics.", "status": "technical-view", "component": "record-table", "records": runtime},
    ]

    return {
        "workspace": {"id": "settings.asterisk", "title": "Asterisk Control Plane", "status": "Live"},
        "subject": {
            "id": "asterisk",
            "key": "asterisk",
            "title": "Asterisk",
            "subtitle": "Global Asterisk infrastructure, apply status and runtime diagnostics.",
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


@app.post("/api/v1/asterisk/provisioning/apply", status_code=status.HTTP_201_CREATED)
def apply_config(payload: ApplyConfigPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            rendered_config = render_asterisk_config(cursor, payload.mode)
            tenant_count = len(rendered_config["tenants"])
            rendered_files = sum(len(tenant.get("files", {})) for tenant in rendered_config["tenants"])
            config_hash = sha256(json.dumps(rendered_config, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            apply_result: dict[str, Any] = {"status": "render_only", "message": "Configuration rendered and recorded without filesystem changes."}
            if payload.mode == "apply":
                apply_result = write_rendered_config_files(rendered_config)

            result_payload = {
                "mode": payload.mode,
                "message": "Configuration rendered and applied to Voxalia-managed Asterisk files." if payload.mode == "apply" else "Configuration rendered and recorded in render-only mode.",
                "tenant_count": tenant_count,
                "rendered_files": rendered_files,
                "config_hash": config_hash,
                "apply": apply_result,
            }
            cursor.execute(
                """
                insert into asterisk.provisioning_jobs (
                  job_type, status, started_at, finished_at, desired_state, result
                )
                values (
                  'apply_config',
                  'succeeded',
                  now(),
                  now(),
                  %(desired_state)s::jsonb,
                  %(result)s::jsonb
                )
                returning id::text;
                """,
                {
                    "desired_state": json.dumps(rendered_config),
                    "result": json.dumps(result_payload),
                },
            )
            job = cursor.fetchone()
            cursor.execute(
                """
                insert into asterisk.config_revisions (
                  revision_key, provisioning_job_id, status, config_hash, rendered_config, applied_at
                )
                values (
                  %(revision_key)s,
                  %(job_id)s,
                  'applied',
                  %(config_hash)s,
                  %(rendered_config)s::jsonb,
                  now()
                )
                returning id::text;
                """,
                {
                    "revision_key": f"global-apply-{job['id']}",
                    "job_id": job["id"],
                    "config_hash": config_hash,
                    "rendered_config": json.dumps(rendered_config),
                },
            )
            revision = cursor.fetchone()
            cursor.execute(
                """
                update asterisk.tenant_voice_profiles
                set last_provisioned_at = now(),
                    status = case when status = 'failed' then 'active' else status end
                where voice_enabled = true
                returning tenant_id;
                """
            )
            applied_tenants = cursor.rowcount
        connection.commit()

    return {
        "job_id": job["id"],
        "revision_id": revision["id"],
        "status": "applied",
        "mode": payload.mode,
        "tenant_count": applied_tenants,
        "rendered_files": rendered_files,
        "config_hash": config_hash,
        "apply": apply_result,
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
                  lq.status,
                  lq.config,
                  count(lqm.id)::int as members
                from asterisk.logical_queues lq
                join asterisk.dial_contexts dc on dc.id = lq.dial_context_id
                left join asterisk.logical_queue_members lqm on lqm.logical_queue_id = lq.id
                where lq.tenant_id = %(tenant_id)s
                group by lq.id, dc.context_key, lq.queue_key, lq.display_name, lq.provider_queue_name, lq.strategy, lq.timeout_seconds, lq.status, lq.config
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
                select
                  id::text,
                  policy_key,
                  display_name,
                  scope_type,
                  coalesce(scope_id, '') as scope_id,
                  recording_required,
                  disclosure_required,
                  retention_days,
                  storage_path_template,
                  status,
                  config
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
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"name": "channel_id", "label": "Channel", "control": "select", "options": [{"value": "", "label": "Any channel"}] + channel_options, "required": False},
                    {"name": "number_id", "label": "Number", "control": "select", "options": [{"value": "", "label": "Any number"}] + number_options, "required": False},
                    {"name": "inbound_context_id", "label": "Inbound context", "control": "select", "options": [{"value": "", "label": "Default inbound context"}] + context_id_options, "required": False},
                    {"name": "target_type", "label": "Target type", "control": "select", "options": [{"value": "queue", "label": "Queue"}, {"value": "extension", "label": "Extension"}, {"value": "context", "label": "Context"}, {"value": "external_number", "label": "External number"}, {"value": "voicemail", "label": "Voicemail"}, {"value": "hangup", "label": "Hangup"}], "defaultValue": "queue"},
                    {"name": "target_id", "label": "Target", "control": "select", "options": route_target_options, "helperText": "Select a target compatible with the target type. External numbers can be edited after creation if needed."},
                    {"name": "priority", "label": "Priority", "type": "number", "defaultValue": "100"},
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
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}, {"value": "provisioning", "label": "Provisioning"}, {"value": "failed", "label": "Failed"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False},
                ],
            },
            "records": routes,
        },
        {
            "id": "recording",
            "label": "Recording",
            "description": "Recording policy intent applied by the Asterisk provisioner.",
            "status": "empty" if not recording else "live",
            "component": "crud-resource",
            "crud": {
                "title": "Recording Policies",
                "eyebrow": "policy",
                "createLabel": "Create policy",
                "createAction": f"/api/settings/asterisk/{profile['tenant_key']}/recording",
                "rowActionBasePath": f"/api/settings/asterisk/{profile['tenant_key']}/recording",
                "identityField": "id",
                "titleField": "policy_key",
                "searchPlaceholder": "Search policy, scope or status",
                "emptyTitle": "No recording policies match the current filters",
                "emptyDescription": "Create a tenant default recording policy before provisioning.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "scope_type", "label": "Scope", "allLabel": "All scopes", "options": [{"value": "tenant", "label": "Tenant"}, {"value": "channel", "label": "Channel"}, {"value": "number", "label": "Number"}, {"value": "queue", "label": "Queue"}, {"value": "extension", "label": "Extension"}]},
                    {"key": "status", "label": "Status", "allLabel": "All statuses", "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}, {"value": "draft", "label": "Draft"}]},
                ],
                "columns": [
                    {"id": "policy_key", "header": "Policy"},
                    {"id": "display_name", "header": "Name"},
                    {"id": "scope_type", "header": "Scope"},
                    {"id": "scope_id", "header": "Scope ID"},
                    {"id": "recording_required", "header": "Record"},
                    {"id": "disclosure_required", "header": "Disclosure"},
                    {"id": "retention_days", "header": "Retention"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"name": "policy_key", "label": "Policy key", "defaultValue": "default"},
                    {"name": "display_name", "label": "Display name", "defaultValue": "Default recording policy"},
                    {"name": "scope_type", "label": "Scope", "control": "select", "options": [{"value": "tenant", "label": "Tenant"}, {"value": "channel", "label": "Channel"}, {"value": "number", "label": "Number"}, {"value": "queue", "label": "Queue"}, {"value": "extension", "label": "Extension"}], "defaultValue": "tenant"},
                    {"name": "scope_id", "label": "Scope ID", "required": False, "helperText": "Leave empty for tenant-wide policy."},
                    {"name": "recording_required", "label": "Record calls", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}], "defaultValue": "true"},
                    {"name": "disclosure_required", "label": "Disclosure required", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}], "defaultValue": "true"},
                    {"name": "retention_days", "label": "Retention days", "type": "number", "defaultValue": "365"},
                    {"name": "storage_path_template", "label": "Storage path template", "required": False},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}, {"value": "draft", "label": "Draft"}], "defaultValue": "active"},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"name": "id", "label": "ID", "editable": False},
                    {"name": "policy_key", "label": "Policy key"},
                    {"name": "display_name", "label": "Display name"},
                    {"name": "scope_type", "label": "Scope", "control": "select", "options": [{"value": "tenant", "label": "Tenant"}, {"value": "channel", "label": "Channel"}, {"value": "number", "label": "Number"}, {"value": "queue", "label": "Queue"}, {"value": "extension", "label": "Extension"}]},
                    {"name": "scope_id", "label": "Scope ID", "required": False, "helperText": "Leave empty for tenant-wide policy."},
                    {"name": "recording_required", "label": "Record calls", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}]},
                    {"name": "disclosure_required", "label": "Disclosure required", "control": "select", "options": [{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}]},
                    {"name": "retention_days", "label": "Retention days", "type": "number"},
                    {"name": "storage_path_template", "label": "Storage path template", "required": False},
                    {"name": "status", "label": "Status", "control": "select", "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}, {"value": "draft", "label": "Draft"}]},
                    {"name": "config", "label": "Config JSON", "control": "json", "required": False},
                ],
            },
            "records": recording,
        },
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
                  strategy, timeout_seconds, status, config
                )
                values (
                  %(tenant_id)s, %(dial_context_id)s, %(queue_key)s, %(display_name)s, %(provider_queue_name)s,
                  %(strategy)s, %(timeout_seconds)s, %(status)s, %(config)s::jsonb
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
                  priority, status, config
                )
                values (
                  %(tenant_id)s, %(channel_id)s, %(number_id)s, %(inbound_context_id)s, %(target_type)s, %(target_id)s,
                  %(priority)s, %(status)s, %(config)s::jsonb
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


@app.post("/api/v1/asterisk/tenants/{tenant_key}/recording", status_code=status.HTTP_201_CREATED)
def create_recording_policy(tenant_key: str, payload: RecordingPolicyPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                insert into asterisk.recording_policies (
                  tenant_id, policy_key, display_name, scope_type, scope_id,
                  recording_required, disclosure_required, retention_days,
                  storage_path_template, status, config
                )
                values (
                  %(tenant_id)s, %(policy_key)s, %(display_name)s, %(scope_type)s, %(scope_id)s,
                  %(recording_required)s, %(disclosure_required)s, %(retention_days)s,
                  %(storage_path_template)s, %(status)s, %(config)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant_id,
                    "policy_key": payload.policy_key,
                    "display_name": payload.display_name,
                    "scope_type": payload.scope_type,
                    "scope_id": payload.scope_id.strip() or None,
                    "recording_required": payload.recording_required,
                    "disclosure_required": payload.disclosure_required,
                    "retention_days": payload.retention_days,
                    "storage_path_template": payload.storage_path_template,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
        connection.commit()
    return {"id": row["id"], "status": "created"}


@app.patch("/api/v1/asterisk/tenants/{tenant_key}/recording/{policy_id}")
def update_recording_policy(tenant_key: str, policy_id: int, payload: RecordingPolicyPayload) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                update asterisk.recording_policies
                set
                  policy_key = %(policy_key)s,
                  display_name = %(display_name)s,
                  scope_type = %(scope_type)s,
                  scope_id = %(scope_id)s,
                  recording_required = %(recording_required)s,
                  disclosure_required = %(disclosure_required)s,
                  retention_days = %(retention_days)s,
                  storage_path_template = %(storage_path_template)s,
                  status = %(status)s,
                  config = %(config)s::jsonb,
                  updated_at = now()
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "id": policy_id,
                    "tenant_id": tenant_id,
                    "policy_key": payload.policy_key,
                    "display_name": payload.display_name,
                    "scope_type": payload.scope_type,
                    "scope_id": payload.scope_id.strip() or None,
                    "recording_required": payload.recording_required,
                    "disclosure_required": payload.disclosure_required,
                    "retention_days": payload.retention_days,
                    "storage_path_template": payload.storage_path_template,
                    "status": payload.status,
                    "config": json.dumps(payload.config),
                },
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording policy not found")
        connection.commit()
    return {"id": row["id"], "status": "updated"}


@app.delete("/api/v1/asterisk/tenants/{tenant_key}/recording/{policy_id}")
def delete_recording_policy(tenant_key: str, policy_id: int) -> dict[str, object]:
    with db() as connection:
        with connection.cursor() as cursor:
            tenant_id = tenant_id_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from asterisk.recording_policies
                where id = %(id)s and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"id": policy_id, "tenant_id": tenant_id},
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording policy not found")
        connection.commit()
    return {"id": row["id"], "status": "deleted"}
