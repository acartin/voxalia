import json
from datetime import UTC
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.config import get_settings
from app.db import db
from app.menu import effective_menu, item_for_path
from app.security import RequestContext, hash_token, make_password_hash, new_session_token, require_context, require_permission, session_expiry, verify_password

app = FastAPI(title="Voxalia Web API")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=240)


class UserCreateRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=80)
    tenant_key: str = Field(min_length=1, max_length=120)
    status: str = Field(default="active", pattern="^(active|inactive|locked)$")
    password: str = Field(min_length=8, max_length=240)


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: str | None = Field(default=None, min_length=1, max_length=80)
    tenant_key: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, pattern="^(active|inactive|locked)$")
    password: str | None = Field(default=None, min_length=8, max_length=240)


class TenantCreateRequest(BaseModel):
    tenant_key: str = Field(min_length=1, max_length=120, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(min_length=1, max_length=160)
    legal_name: str | None = Field(default=None, max_length=240)
    vertical: str = Field(default="hospitality", pattern="^(hospitality|internal|other)$")
    country_code: str = Field(default="CR", min_length=2, max_length=2)
    timezone: str = Field(default="America/Costa_Rica", min_length=1, max_length=120)
    status: str = Field(default="active", pattern="^(active|inactive|suspended)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    legal_name: str | None = Field(default=None, max_length=240)
    vertical: str | None = Field(default=None, pattern="^(hospitality|internal|other)$")
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, pattern="^(active|inactive|suspended)$")
    metadata: dict[str, Any] | None = None


class TenantChannelRequest(BaseModel):
    channel_key: str = Field(min_length=1, max_length=120, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$")
    channel_type: str = Field(pattern="^(voice_toll_free|voice_local|chatwoot_inbox|voxalia_webchat|meta_whatsapp|email)$")
    display_name: str = Field(min_length=1, max_length=160)
    provider: str = Field(default="voxalia", min_length=1, max_length=120)
    routing_key: str = Field(default="", max_length=240)
    service_policy_id: int | None = None
    default_language: str = Field(default="en", min_length=1, max_length=12)
    recording_required: bool = True
    status: str = Field(default="active", pattern="^(active|inactive|provisioning|failed)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceNumberRequest(BaseModel):
    channel_id: int | None = None
    number_e164: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=160)
    number_type: str = Field(pattern="^(toll_free|local|extension|outbound_caller_id)$")
    country_code: str = Field(default="US", min_length=2, max_length=2)
    status: str = Field(default="active", pattern="^(active|inactive|provisioning|failed|released)$")
    recording_required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantContactRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    organization: str = Field(default="", max_length=160)
    department: str = Field(default="", max_length=160)
    title: str = Field(default="", max_length=160)
    contact_type: str = Field(default="other", pattern="^(admin|billing|operations|reservations|sales|emergency|reporting|technical|other)$")
    priority: int = Field(default=100, ge=0)
    status: str = Field(default="active", pattern="^(active|inactive)$")
    notes: str = Field(default="", max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantContactMethodRequest(BaseModel):
    contact_id: int
    method_type: str = Field(pattern="^(phone|email|sms|whatsapp|extension)$")
    label: str = Field(default="", max_length=160)
    value: str = Field(min_length=1, max_length=240)
    is_primary: bool = False
    can_receive_escalations: bool = False
    availability: str = Field(default="", max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentProfileRequest(BaseModel):
    user_id: int
    display_name: str = Field(min_length=1, max_length=160)
    languages: str | list[str] = Field(default_factory=lambda: ["en"])
    skills: str | list[str] = Field(default_factory=list)
    status: str = Field(default="offline", pattern="^(offline|available|ringing|on_call|after_call_work|break|training|unavailable)$")
    supervisor_user_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantAgentAssignmentRequest(BaseModel):
    tenant_id: int
    assignment_type: str = Field(default="primary", pattern="^(primary|backup|supervisor|specialist)$")
    queue_key: str = Field(default="", max_length=120)
    priority: int = Field(default=100, ge=0)
    status: str = Field(default="active", pattern="^(active|inactive)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExtensionAssignmentRequest(BaseModel):
    tenant_id: int
    logical_extension_id: int
    status: str = Field(default="active", pattern="^(active|inactive|provisioning|failed)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SimulateRoleRequest(BaseModel):
    role_id: str = Field(min_length=1, max_length=80)


@app.on_event("startup")
def bootstrap_admin() -> None:
    settings = get_settings()
    if not (settings.bootstrap_admin_username and settings.bootstrap_admin_email and settings.bootstrap_admin_password):
        return

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.tenants where tenant_key = 'voxalia';")
            tenant = cursor.fetchone()
            if not tenant:
                return

            cursor.execute(
                "select id from public.auth_users where lower(username) = lower(%(username)s);",
                {"username": settings.bootstrap_admin_username},
            )
            user = cursor.fetchone()
            if user:
                cursor.execute(
                    """
                    update public.auth_users
                    set email = %(email)s,
                        password_hash = %(password_hash)s,
                        status = 'active',
                        updated_at = now()
                    where id = %(user_id)s
                    returning id;
                    """,
                    {
                        "user_id": user["id"],
                        "email": settings.bootstrap_admin_email,
                        "password_hash": make_password_hash(settings.bootstrap_admin_password),
                    },
                )
                user = cursor.fetchone()
            else:
                cursor.execute(
                    """
                    insert into public.auth_users (username, email, display_name, password_hash, status)
                    values (%(username)s, %(email)s, 'Voxalia Admin', %(password_hash)s, 'active')
                    returning id;
                    """,
                    {
                        "username": settings.bootstrap_admin_username,
                        "email": settings.bootstrap_admin_email,
                        "password_hash": make_password_hash(settings.bootstrap_admin_password),
                    },
                )
                user = cursor.fetchone()
            cursor.execute(
                """
                insert into public.auth_user_roles (user_id, role_id)
                values (%(user_id)s, 'system_admin')
                on conflict do nothing;
                """,
                {"user_id": user["id"]},
            )
            cursor.execute(
                """
                insert into public.auth_user_tenants (user_id, tenant_id, is_default)
                values (%(user_id)s, %(tenant_id)s, true)
                on conflict (user_id, tenant_id) do update set is_default = true;
                """,
                {"user_id": user["id"], "tenant_id": tenant["id"]},
            )
            connection.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest) -> dict[str, str]:
    login_value = payload.username.strip()
    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id, username, email, password_hash, status
                from public.auth_users
                where lower(username) = lower(%(login)s)
                   or lower(email) = lower(%(login)s);
                """,
                {"login": login_value},
            )
            user = cursor.fetchone()
            if not user or user["status"] != "active" or not verify_password(payload.password, user["password_hash"]):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

            cursor.execute(
                """
                select ur.role_id, ut.tenant_id
                from public.auth_user_roles ur
                cross join lateral (
                  select tenant_id
                  from public.auth_user_tenants
                  where user_id = %(user_id)s
                  order by is_default desc, tenant_id asc
                  limit 1
                ) ut
                where ur.user_id = %(user_id)s
                order by ur.role_id asc
                limit 1;
                """,
                {"user_id": user["id"]},
            )
            context = cursor.fetchone()
            if not context:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no role or tenant assignment")

            token = new_session_token()
            expires_at = session_expiry()
            cursor.execute(
                """
                insert into public.auth_sessions (user_id, session_token_hash, active_tenant_id, active_role_id, expires_at)
                values (%(user_id)s, %(token_hash)s, %(tenant_id)s, %(role_id)s, %(expires_at)s);
                """,
                {
                    "user_id": user["id"],
                    "token_hash": hash_token(token),
                    "tenant_id": context["tenant_id"],
                    "role_id": context["role_id"],
                    "expires_at": expires_at,
                },
            )
            connection.commit()

    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at.astimezone(UTC).isoformat()}


@app.post("/api/v1/auth/logout")
def logout(payload: dict[str, str]) -> dict[str, str]:
    token = payload.get("token", "")
    if token:
        with db() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "update public.auth_sessions set revoked_at = now() where session_token_hash = %(token_hash)s;",
                    {"token_hash": hash_token(token)},
                )
                connection.commit()
    return {"status": "ok"}


@app.post("/api/v1/auth/simulate-role")
def simulate_role(payload: SimulateRoleRequest, context: RequestContext = Depends(require_context)) -> dict[str, str]:
    if not context.can_simulate_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin role is required")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.auth_roles where id = %(role_id)s;", {"role_id": payload.role_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")

            cursor.execute(
                """
                update public.auth_sessions
                set active_role_id = %(role_id)s,
                    last_seen_at = now()
                where session_token_hash = %(token_hash)s
                  and user_id = %(user_id)s
                  and revoked_at is null
                  and expires_at > now();
                """,
                {
                    "role_id": payload.role_id,
                    "token_hash": context.token_hash,
                    "user_id": context.user_id,
                },
            )
            connection.commit()

    return {"status": "ok", "role_id": payload.role_id}


@app.get("/api/v1/menu")
def menu(context: RequestContext = Depends(require_context)) -> dict[str, object]:
    return {
        "user": {
            "id": str(context.user_id),
            "email": context.email,
            "role": context.role,
            "role_label": context.role_label,
        },
        "tenant": {
            "client_id": context.tenant_key,
            "name": context.tenant_name,
            "mode": "active",
        },
        "auth": {
            "provider": "voxalia-web-api",
            "status": "active",
            "can_simulate_roles": context.can_simulate_roles,
            "is_role_simulated": context.is_role_simulated,
        },
        "sections": effective_menu(context.permissions),
    }


@app.get("/api/v1/settings/users")
def users_module(context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")
    item = item_for_path("/settings/users")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  u.id::text,
                  u.username,
                  u.email,
                  u.display_name,
                  coalesce(min(r.id), '') as role,
                  coalesce(min(r.label), '') as role_label,
                  coalesce(min(t.tenant_key), '') as tenant_key,
                  coalesce(min(t.display_name), '') as tenant_name,
                  coalesce(min(r.scope), 'tenant') as tenant_scope,
                  u.status,
                  max(s.last_seen_at)::text as last_seen_at
                from public.auth_users u
                left join public.auth_user_roles ur on ur.user_id = u.id
                left join public.auth_roles r on r.id = ur.role_id
                left join public.auth_user_tenants ut on ut.user_id = u.id
                left join public.tenants t on t.id = ut.tenant_id
                left join public.auth_sessions s on s.user_id = u.id and s.revoked_at is null
                group by u.id, u.username, u.email, u.display_name, u.status
                order by u.updated_at desc, u.id desc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]

    return {
        "module": {
            "id": "settings.users",
            "title": item["label"] if item else "Users",
            "description": item["description"] if item else "Users and account lifecycle.",
            "status": "Live",
        },
        "context": {"client_id": context.tenant_key, "role": context.role},
        "links": {},
        "actions": [{"id": "create", "label": "Create user", "enabled": True, "permission": "auth:users:manage"}],
        "records": records,
    }


@app.get("/api/v1/settings/tenants")
def tenants_module(context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "tenants:manage")
    item = item_for_path("/settings/tenants")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  t.id::text,
                  t.tenant_key,
                  t.display_name,
                  coalesce(t.legal_name, '') as legal_name,
                  t.vertical,
                  t.country_code,
                  coalesce(cc.display_name, '') as country,
                  t.timezone,
                  t.status,
                  t.metadata,
                  count(ut.user_id)::int as users,
                  t.updated_at::text as updated_at
                from public.tenants t
                left join public.country_catalog cc on cc.country_code = t.country_code
                left join public.auth_user_tenants ut on ut.tenant_id = t.id
                group by t.id, t.tenant_key, t.display_name, t.legal_name, t.vertical,
                         t.country_code, cc.display_name, t.timezone, t.status, t.updated_at
                order by t.display_name asc, t.id asc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]
            filters = {"country_options": country_options(cursor)}

    return {
        "module": {
            "id": "settings.tenants",
            "title": item["label"] if item else "Tenants",
            "description": item["description"] if item else "Partners, policies and tenant workspaces.",
            "status": "Live",
        },
        "context": {"client_id": context.tenant_key, "role": context.role},
        "links": {},
        "actions": [{"id": "create", "label": "Create tenant", "enabled": True, "permission": "tenants:manage"}],
        "filters": filters,
        "records": records,
    }


@app.post("/api/v1/settings/tenants", status_code=201)
def create_tenant(payload: TenantCreateRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select id from public.tenants where tenant_key = %(tenant_key)s;",
                {"tenant_key": payload.tenant_key},
            )
            if cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant key already exists")

            country_code = ensure_country_code(cursor, payload.country_code)
            cursor.execute(
                """
                insert into public.tenants (
                  tenant_key, display_name, legal_name, vertical, country_code, timezone, status, metadata
                )
                values (
                  %(tenant_key)s, %(display_name)s, %(legal_name)s, %(vertical)s, %(country_code)s,
                  %(timezone)s, %(status)s, %(metadata)s::jsonb
                )
                returning id::text, tenant_key, display_name, coalesce(legal_name, '') as legal_name,
                          vertical, country_code, timezone, status, metadata;
                """,
                {
                    "tenant_key": payload.tenant_key,
                    "display_name": payload.display_name,
                    "legal_name": payload.legal_name or None,
                    "vertical": payload.vertical,
                    "country_code": country_code,
                    "timezone": payload.timezone,
                    "status": payload.status,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            tenant = dict(cursor.fetchone())
            cursor.execute(
                """
                insert into asterisk.tenant_voice_profiles (
                  tenant_id,
                  voice_enabled,
                  provisioning_mode,
                  namespace_key,
                  default_context_prefix,
                  default_extension_prefix,
                  status,
                  metadata
                )
                values (
                  %(tenant_id)s,
                  true,
                  'generated',
                  %(tenant_key)s,
                  %(default_context_prefix)s,
                  '',
                  'active',
                  '{"created_by":"tenant-crud"}'::jsonb
                )
                on conflict (tenant_id) do nothing;
                """,
                {
                    "tenant_id": tenant["id"],
                    "tenant_key": tenant["tenant_key"],
                    "default_context_prefix": "tenant_" + tenant["tenant_key"].replace("-", "_"),
                },
            )
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.create', 'tenant', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": tenant["id"]},
            )
            connection.commit()

    return tenant


@app.patch("/api/v1/settings/tenants/{tenant_id}")
def update_tenant(tenant_id: int, payload: TenantUpdateRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    update_values = payload.model_dump(exclude_unset=True)
    if not update_values:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No tenant fields were provided")

    with db() as connection:
        with connection.cursor() as cursor:
            country_code = ensure_country_code(cursor, update_values["country_code"]) if "country_code" in update_values else None
            cursor.execute(
                """
                update public.tenants
                set
                  display_name = coalesce(%(display_name)s, display_name),
                  legal_name = case when %(has_legal_name)s then %(legal_name)s else legal_name end,
                  vertical = coalesce(%(vertical)s, vertical),
                  country_code = coalesce(%(country_code)s, country_code),
                  timezone = coalesce(%(timezone)s, timezone),
                  status = coalesce(%(status)s, status),
                  metadata = coalesce(%(metadata)s::jsonb, metadata),
                  updated_at = now()
                where id = %(tenant_id)s
                returning id::text, tenant_key, display_name, coalesce(legal_name, '') as legal_name,
                          vertical, country_code, timezone, status, metadata;
                """,
                {
                    "tenant_id": tenant_id,
                    "display_name": update_values.get("display_name"),
                    "legal_name": update_values.get("legal_name"),
                    "has_legal_name": "legal_name" in update_values,
                    "vertical": update_values.get("vertical"),
                    "country_code": country_code,
                    "timezone": update_values.get("timezone"),
                    "status": update_values.get("status"),
                    "metadata": json.dumps(update_values["metadata"]) if "metadata" in update_values else None,
                },
            )
            tenant = cursor.fetchone()
            if not tenant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.update', 'tenant', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant_id, "subject_id": str(tenant_id)},
            )
            connection.commit()

    return dict(tenant)


@app.delete("/api/v1/settings/tenants/{tenant_id}")
def delete_tenant(tenant_id: int, context: RequestContext = Depends(require_context)) -> dict[str, str]:
    require_permission(context, "tenants:manage")

    if tenant_id == context.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the active tenant for the current session")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from public.tenants where id = %(tenant_id)s returning id::text;", {"tenant_id": tenant_id})
            deleted = cursor.fetchone()
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(actor_tenant_id)s, 'tenant.delete', 'tenant', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "actor_tenant_id": context.tenant_id, "subject_id": deleted["id"]},
            )
            connection.commit()

    return {"status": "deleted", "id": deleted["id"]}


@app.get("/api/v1/settings/agents")
def agents_module(context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")
    item = item_for_path("/settings/agents")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  ap.id::text,
                  ap.user_id::text,
                  u.display_name as user_name,
                  u.email as user_email,
                  ap.display_name,
                  array_to_string(ap.languages, ', ') as languages,
                  array_to_string(ap.skills, ', ') as skills,
                  ap.status,
                  coalesce(su.display_name, '') as supervisor,
                  coalesce(ap.supervisor_user_id::text, '') as supervisor_user_id,
                  count(taa.id)::int as tenants_assigned,
                  ap.metadata,
                  ap.updated_at::text as updated_at
                from public.agent_profiles ap
                join public.auth_users u on u.id = ap.user_id
                left join public.auth_users su on su.id = ap.supervisor_user_id
                left join public.tenant_agent_assignments taa
                  on taa.agent_profile_id = ap.id
                 and taa.status = 'active'
                group by ap.id, ap.user_id, u.display_name, u.email, ap.display_name,
                         ap.languages, ap.skills, ap.status, su.display_name,
                         ap.supervisor_user_id, ap.metadata, ap.updated_at
                order by ap.display_name asc, ap.id asc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]
            filters = {"user_options": user_options(cursor)}

    return {
        "module": {
            "id": "settings.agents",
            "title": item["label"] if item else "Agents",
            "description": item["description"] if item else "Voxalia operator profiles and tenant assignments.",
            "status": "Live",
        },
        "context": {"client_id": context.tenant_key, "role": context.role},
        "links": {},
        "actions": [{"id": "create", "label": "Create agent", "enabled": True, "permission": "auth:users:manage"}],
        "filters": filters,
        "records": records,
    }


@app.post("/api/v1/settings/agents", status_code=201)
def create_agent(payload: AgentProfileRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.auth_users where id = %(user_id)s;", {"user_id": payload.user_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown user")

            if payload.supervisor_user_id:
                cursor.execute("select id from public.auth_users where id = %(user_id)s;", {"user_id": payload.supervisor_user_id})
                if not cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown supervisor user")

            cursor.execute(
                """
                insert into public.agent_profiles (
                  user_id, display_name, languages, skills, status, supervisor_user_id, metadata
                )
                values (
                  %(user_id)s, %(display_name)s, %(languages)s, %(skills)s, %(status)s,
                  %(supervisor_user_id)s, %(metadata)s::jsonb
                )
                returning id::text, user_id::text, display_name, array_to_string(languages, ', ') as languages,
                          array_to_string(skills, ', ') as skills, status, coalesce(supervisor_user_id::text, '') as supervisor_user_id,
                          metadata, updated_at::text as updated_at;
                """,
                {
                    "user_id": payload.user_id,
                    "display_name": payload.display_name,
                    "languages": normalize_text_list(payload.languages),
                    "skills": normalize_text_list(payload.skills),
                    "status": payload.status,
                    "supervisor_user_id": payload.supervisor_user_id,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            agent = dict(cursor.fetchone())
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.create', 'agent_profile', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": context.tenant_id, "subject_id": agent["id"]},
            )
            connection.commit()

    return agent


@app.patch("/api/v1/settings/agents/{agent_id}")
def update_agent(agent_id: int, payload: AgentProfileRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.auth_users where id = %(user_id)s;", {"user_id": payload.user_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown user")

            if payload.supervisor_user_id:
                cursor.execute("select id from public.auth_users where id = %(user_id)s;", {"user_id": payload.supervisor_user_id})
                if not cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown supervisor user")

            cursor.execute(
                """
                update public.agent_profiles
                set
                  user_id = %(user_id)s,
                  display_name = %(display_name)s,
                  languages = %(languages)s,
                  skills = %(skills)s,
                  status = %(status)s,
                  supervisor_user_id = %(supervisor_user_id)s,
                  metadata = %(metadata)s::jsonb,
                  updated_at = now()
                where id = %(agent_id)s
                returning id::text, user_id::text, display_name, array_to_string(languages, ', ') as languages,
                          array_to_string(skills, ', ') as skills, status, coalesce(supervisor_user_id::text, '') as supervisor_user_id,
                          metadata, updated_at::text as updated_at;
                """,
                {
                    "agent_id": agent_id,
                    "user_id": payload.user_id,
                    "display_name": payload.display_name,
                    "languages": normalize_text_list(payload.languages),
                    "skills": normalize_text_list(payload.skills),
                    "status": payload.status,
                    "supervisor_user_id": payload.supervisor_user_id,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            agent = cursor.fetchone()
            if not agent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.update', 'agent_profile', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": context.tenant_id, "subject_id": str(agent_id)},
            )
            connection.commit()

    return dict(agent)


@app.delete("/api/v1/settings/agents/{agent_id}")
def delete_agent(agent_id: int, context: RequestContext = Depends(require_context)) -> dict[str, str]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from public.agent_profiles where id = %(agent_id)s returning id::text;", {"agent_id": agent_id})
            deleted = cursor.fetchone()
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.delete', 'agent_profile', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": context.tenant_id, "subject_id": deleted["id"]},
            )
            connection.commit()

    return {"status": "deleted", "id": deleted["id"]}


@app.post("/api/v1/settings/users", status_code=201)
def create_user(payload: UserCreateRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")
    username = payload.email.split("@", 1)[0]

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.auth_roles where id = %(role)s;", {"role": payload.role})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")

            cursor.execute("select id from public.tenants where tenant_key = %(tenant_key)s;", {"tenant_key": payload.tenant_key})
            tenant = cursor.fetchone()
            if not tenant:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown tenant")

            cursor.execute(
                """
                insert into public.auth_users (username, email, display_name, password_hash, status)
                values (%(username)s, %(email)s, %(display_name)s, %(password_hash)s, %(status)s)
                returning id::text, username, email, display_name, status;
                """,
                {
                    "username": username,
                    "email": str(payload.email),
                    "display_name": payload.display_name,
                    "password_hash": make_password_hash(payload.password),
                    "status": payload.status,
                },
            )
            user = dict(cursor.fetchone())
            cursor.execute(
                "insert into public.auth_user_roles (user_id, role_id) values (%(user_id)s, %(role_id)s);",
                {"user_id": user["id"], "role_id": payload.role},
            )
            cursor.execute(
                "insert into public.auth_user_tenants (user_id, tenant_id, is_default) values (%(user_id)s, %(tenant_id)s, true);",
                {"user_id": user["id"], "tenant_id": tenant["id"]},
            )
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'auth.user.create', 'auth_user', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": context.tenant_id, "subject_id": user["id"]},
            )
            connection.commit()

    return user


@app.patch("/api/v1/settings/users/{user_id}")
def update_user(user_id: int, payload: UserUpdateRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            password_hash = make_password_hash(payload.password) if payload.password else None
            cursor.execute(
                """
                update public.auth_users
                set
                  display_name = coalesce(%(display_name)s, display_name),
                  password_hash = coalesce(%(password_hash)s, password_hash),
                  status = coalesce(%(status)s, status),
                  updated_at = now()
                where id = %(user_id)s
                returning id::text, username, email, display_name, status;
                """,
                {
                    "user_id": user_id,
                    "display_name": payload.display_name,
                    "password_hash": password_hash,
                    "status": payload.status,
                },
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            if payload.role:
                cursor.execute("select id from public.auth_roles where id = %(role)s;", {"role": payload.role})
                if not cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role")
                cursor.execute("delete from public.auth_user_roles where user_id = %(user_id)s;", {"user_id": user_id})
                cursor.execute(
                    "insert into public.auth_user_roles (user_id, role_id) values (%(user_id)s, %(role_id)s);",
                    {"user_id": user_id, "role_id": payload.role},
                )

            if payload.tenant_key:
                cursor.execute("select id from public.tenants where tenant_key = %(tenant_key)s;", {"tenant_key": payload.tenant_key})
                tenant = cursor.fetchone()
                if not tenant:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown tenant")
                cursor.execute("delete from public.auth_user_tenants where user_id = %(user_id)s;", {"user_id": user_id})
                cursor.execute(
                    "insert into public.auth_user_tenants (user_id, tenant_id, is_default) values (%(user_id)s, %(tenant_id)s, true);",
                    {"user_id": user_id, "tenant_id": tenant["id"]},
                )

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'auth.user.update', 'auth_user', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": context.tenant_id, "subject_id": str(user_id)},
            )
            connection.commit()

    return dict(user)


def tenant_for_key(cursor, tenant_key: str) -> dict[str, Any]:
    cursor.execute(
        """
        select id, id::text as id_text, tenant_key, display_name, legal_name, vertical, country_code, timezone, status
        from public.tenants
        where tenant_key = %(tenant_key)s;
        """,
        {"tenant_key": tenant_key},
    )
    tenant = cursor.fetchone()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return dict(tenant)


def country_options(cursor) -> list[dict[str, str]]:
    cursor.execute(
        """
        select
          country_code as value,
          display_name || ' (' || iso_alpha3 || ')' as label
        from public.country_catalog
        where status = 'active'
        order by sort_order asc, display_name asc;
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def user_options(cursor) -> list[dict[str, str]]:
    cursor.execute(
        """
        select
          u.id::text as value,
          u.display_name || ' <' || u.email || '>' as label
        from public.auth_users u
        where u.status = 'active'
        order by u.display_name asc, u.email asc;
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def tenant_options(cursor) -> list[dict[str, str]]:
    cursor.execute(
        """
        select
          t.id::text as value,
          t.display_name || ' (' || t.tenant_key || ')' as label
        from public.tenants t
        where t.status = 'active'
        order by t.display_name asc, t.tenant_key asc;
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def normalize_text_list(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


def ensure_country_code(cursor, country_code: str | None) -> str:
    normalized_country_code = (country_code or "").strip().upper()
    if not normalized_country_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Country is required")

    cursor.execute(
        """
        select country_code
        from public.country_catalog
        where country_code = %(country_code)s
          and status = 'active';
        """,
        {"country_code": normalized_country_code},
    )
    country = cursor.fetchone()
    if not country:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown country")
    return country["country_code"]


def ensure_service_policy(cursor, tenant_id: int, service_policy_id: int | None) -> None:
    if service_policy_id is None:
        return
    cursor.execute(
        "select id from public.tenant_service_policies where id = %(id)s and tenant_id = %(tenant_id)s;",
        {"id": service_policy_id, "tenant_id": tenant_id},
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown service policy for tenant")


def ensure_tenant_channel(cursor, tenant_id: int, channel_id: int | None) -> None:
    if channel_id is None:
        return
    cursor.execute(
        "select id from public.tenant_channels where id = %(id)s and tenant_id = %(tenant_id)s;",
        {"id": channel_id, "tenant_id": tenant_id},
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown channel for tenant")


def ensure_tenant_contact(cursor, tenant_id: int, contact_id: int) -> None:
    cursor.execute(
        "select id from public.tenant_contacts where id = %(id)s and tenant_id = %(tenant_id)s;",
        {"id": contact_id, "tenant_id": tenant_id},
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown contact for tenant")


def tenant_channel_options(cursor, tenant_id: int) -> list[dict[str, str]]:
    cursor.execute(
        """
        select id::text as value, display_name || ' (' || channel_type || ')' as label
        from public.tenant_channels
        where tenant_id = %(tenant_id)s and status = 'active'
        order by display_name asc, id asc;
        """,
        {"tenant_id": tenant_id},
    )
    return [dict(row) for row in cursor.fetchall()]


def tenant_policy_options(cursor, tenant_id: int) -> list[dict[str, str]]:
    cursor.execute(
        """
        select id::text as value, display_name as label
        from public.tenant_service_policies
        where tenant_id = %(tenant_id)s and status = 'active'
        order by display_name asc, id asc;
        """,
        {"tenant_id": tenant_id},
    )
    return [{"value": "", "label": "No policy"}] + [dict(row) for row in cursor.fetchall()]


@app.get("/api/v1/settings/tenants/{tenant_key}/workspace")
def tenant_workspace(tenant_key: str, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)

            cursor.execute(
                """
                select count(*)::int as users
                from public.auth_user_tenants
                where tenant_id = %(tenant_id)s;
                """,
                {"tenant_id": tenant["id"]},
            )
            user_count = cursor.fetchone()["users"]
            cursor.execute(
                """
                select
                  (select count(*)::int from public.tenant_product_subscriptions where tenant_id = %(tenant_id)s and status in ('active', 'trial')) as products,
                  (select count(*)::int from public.tenant_service_policies where tenant_id = %(tenant_id)s and status = 'active') as policies,
                  (select count(*)::int from public.tenant_channels where tenant_id = %(tenant_id)s and status = 'active') as channels,
                  (select count(*)::int from public.voice_numbers where tenant_id = %(tenant_id)s and status = 'active') as numbers,
                  (select count(*)::int from public.tenant_contacts where tenant_id = %(tenant_id)s and status = 'active') as contacts,
                  (select count(*)::int from public.tenant_agent_assignments where tenant_id = %(tenant_id)s and status = 'active') as agents,
                  (select count(*)::int from public.tenant_scripts where tenant_id = %(tenant_id)s and status = 'active') as scripts,
                  (select count(*)::int from public.reporting_recipients where tenant_id = %(tenant_id)s and status = 'active') as reporting_recipients;
                """,
                {"tenant_id": tenant["id"]},
            )
            workspace_counts = cursor.fetchone()
            policy_options = tenant_policy_options(cursor, tenant["id"])
            channel_options = tenant_channel_options(cursor, tenant["id"])
            countries = country_options(cursor)
            cursor.execute(
                """
                select
                  tc.id::text,
                  tc.channel_key,
                  tc.channel_type,
                  tc.display_name,
                  tc.provider,
                  tc.routing_key,
                  case
                    when tc.channel_type in ('voice_toll_free', 'voice_local') then ''
                    else tc.routing_key
                  end as external_key,
                  tc.service_policy_id::text,
                  coalesce(tsp.display_name, '') as service_policy,
                  tc.default_language,
                  tc.recording_required,
                  tc.status,
                  tc.metadata,
                  tc.updated_at::text
                from public.tenant_channels tc
                left join public.tenant_service_policies tsp
                  on tsp.id = tc.service_policy_id
                 and tsp.tenant_id = tc.tenant_id
                where tc.tenant_id = %(tenant_id)s
                order by tc.display_name asc, tc.id asc;
                """,
                {"tenant_id": tenant["id"]},
            )
            channel_records = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select
                  vn.id::text,
                  vn.number_e164,
                  vn.label,
                  vn.number_type,
                  vn.country_code,
                  coalesce(cc.display_name, '') as country,
                  vn.channel_id::text,
                  coalesce(tc.display_name, '') as channel,
                  coalesce(tc.channel_type, '') as channel_type,
                  vn.recording_required,
                  vn.status,
                  vn.metadata,
                  vn.updated_at::text
                from public.voice_numbers vn
                left join public.tenant_channels tc
                  on tc.id = vn.channel_id
                 and tc.tenant_id = vn.tenant_id
                left join public.country_catalog cc on cc.country_code = vn.country_code
                where vn.tenant_id = %(tenant_id)s
                order by vn.number_e164 asc, vn.id asc;
                """,
                {"tenant_id": tenant["id"]},
            )
            number_records = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select
                  c.id::text,
                  c.display_name,
                  c.organization,
                  c.department,
                  c.title,
                  c.contact_type,
                  c.priority,
                  c.status,
                  c.notes,
                  c.metadata,
                  count(cm.id)::int as methods,
                  jsonb_build_array(
                    jsonb_build_object('label', 'Methods', 'href', '/settings/tenants/' || %(tenant_key)s || '?tab=contact-methods&contact_id=' || c.id::text)
                  ) as _actions,
                  c.updated_at::text
                from public.tenant_contacts c
                left join public.tenant_contact_methods cm
                  on cm.contact_id = c.id
                 and cm.tenant_id = c.tenant_id
                where c.tenant_id = %(tenant_id)s
                group by c.id, c.display_name, c.organization, c.department, c.title,
                         c.contact_type, c.priority, c.status, c.notes, c.metadata, c.updated_at
                order by c.priority asc, c.display_name asc, c.id asc;
                """,
                {"tenant_id": tenant["id"], "tenant_key": tenant["tenant_key"]},
            )
            contact_records = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select
                  cm.id::text,
                  cm.contact_id::text,
                  c.display_name as contact,
                  cm.method_type,
                  cm.label,
                  cm.value,
                  cm.is_primary,
                  cm.can_receive_escalations,
                  cm.availability,
                  cm.metadata,
                  cm.updated_at::text
                from public.tenant_contact_methods cm
                join public.tenant_contacts c
                  on c.id = cm.contact_id
                 and c.tenant_id = cm.tenant_id
                where cm.tenant_id = %(tenant_id)s
                order by c.priority asc, c.display_name asc, cm.is_primary desc, cm.method_type asc, cm.id asc;
                """,
                {"tenant_id": tenant["id"]},
            )
            contact_method_records = [dict(row) for row in cursor.fetchall()]

    channel_type_options = [
        {"value": "voice_toll_free", "label": "Voice toll-free"},
        {"value": "voice_local", "label": "Voice local"},
        {"value": "chatwoot_inbox", "label": "Chatwoot inbox"},
        {"value": "voxalia_webchat", "label": "Voxalia webchat"},
        {"value": "meta_whatsapp", "label": "Meta WhatsApp"},
        {"value": "email", "label": "Email"},
    ]
    provider_options = [
        {"value": "voxalia", "label": "Voxalia"},
        {"value": "asterisk", "label": "Asterisk"},
        {"value": "chatwoot", "label": "Chatwoot"},
        {"value": "meta", "label": "Meta"},
        {"value": "email", "label": "Email"},
    ]
    language_options = [
        {"value": "en", "label": "English"},
        {"value": "es", "label": "Spanish"},
        {"value": "fr", "label": "French"},
    ]
    boolean_options = [
        {"value": "true", "label": "Yes"},
        {"value": "false", "label": "No"},
    ]
    channel_status_options = [
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"},
        {"value": "provisioning", "label": "Provisioning"},
        {"value": "failed", "label": "Failed"},
    ]
    number_type_options = [
        {"value": "toll_free", "label": "Toll-free"},
        {"value": "local", "label": "Local DID"},
        {"value": "extension", "label": "Extension"},
        {"value": "outbound_caller_id", "label": "Outbound caller ID"},
    ]
    number_status_options = [
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"},
        {"value": "provisioning", "label": "Provisioning"},
        {"value": "failed", "label": "Failed"},
        {"value": "released", "label": "Released"},
    ]
    contact_type_options = [
        {"value": "admin", "label": "Admin"},
        {"value": "billing", "label": "Billing"},
        {"value": "operations", "label": "Operations"},
        {"value": "reservations", "label": "Reservations"},
        {"value": "sales", "label": "Sales"},
        {"value": "emergency", "label": "Emergency"},
        {"value": "reporting", "label": "Reporting"},
        {"value": "technical", "label": "Technical"},
        {"value": "other", "label": "Other"},
    ]
    contact_method_type_options = [
        {"value": "phone", "label": "Phone"},
        {"value": "email", "label": "Email"},
        {"value": "sms", "label": "SMS"},
        {"value": "whatsapp", "label": "WhatsApp"},
        {"value": "extension", "label": "Extension"},
    ]
    contact_status_options = [
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"},
    ]
    contact_options = [
        {"value": str(row["id"]), "label": f"{row['display_name']} ({row['contact_type']})"}
        for row in contact_records
    ]

    sections = [
        {
            "id": "overview",
            "label": "Overview",
            "description": "Core tenant profile, status and operational ownership.",
            "status": "placeholder",
            "component": "details",
            "records": [],
        },
        {
            "id": "numbers",
            "label": "Voice Numbers",
            "description": "Toll-free numbers, local DIDs and outbound caller IDs assigned to this tenant.",
            "status": "live",
            "component": "crud-grid",
            "records": number_records,
            "crud": {
                "title": "Voice Numbers",
                "description": "Tenant-owned voice numbers before Asterisk routing maps them into contexts, queues or extensions.",
                "eyebrow": "number",
                "createLabel": "Create number",
                "createAction": f"/api/settings/tenants/{tenant_key}/numbers",
                "rowActionBasePath": f"/api/settings/tenants/{tenant_key}/numbers",
                "identityField": "id",
                "titleField": "number_e164",
                "searchPlaceholder": "Search number, label, channel or country",
                "emptyTitle": "No numbers match the current filters",
                "emptyDescription": "Create a channel first, then assign numbers to it.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "number_type", "label": "Type", "allLabel": "All number types", "options": number_type_options},
                    {"key": "country_code", "label": "Country", "allLabel": "All countries", "options": countries},
                    {"key": "status", "label": "Status", "allLabel": "All statuses", "options": number_status_options},
                ],
                "columns": [
                    {"id": "number_e164", "header": "Number"},
                    {"id": "label", "header": "Label"},
                    {"id": "number_type", "header": "Type"},
                    {"id": "channel", "header": "Channel"},
                    {"id": "country", "header": "Country"},
                    {"id": "recording_required", "header": "Recording"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"label": "Number E.164", "name": "number_e164", "placeholder": "+18005550100"},
                    {"label": "Label", "name": "label", "placeholder": "Main toll-free"},
                    {"label": "Number type", "name": "number_type", "control": "select", "options": number_type_options, "defaultValue": "toll_free"},
                    {"label": "Channel", "name": "channel_id", "control": "select", "options": channel_options},
                    {"label": "Country", "name": "country_code", "control": "select", "options": countries, "defaultValue": tenant["country_code"]},
                    {"label": "Recording required", "name": "recording_required", "control": "select", "options": boolean_options, "defaultValue": "true"},
                    {"label": "Status", "name": "status", "control": "select", "options": number_status_options, "defaultValue": "active"},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"label": "Number E.164", "name": "number_e164"},
                    {"label": "Label", "name": "label"},
                    {"label": "Number type", "name": "number_type", "control": "select", "options": number_type_options},
                    {"label": "Channel", "name": "channel_id", "control": "select", "options": channel_options},
                    {"label": "Country", "name": "country_code", "control": "select", "options": countries},
                    {"label": "Recording required", "name": "recording_required", "control": "select", "options": boolean_options},
                    {"label": "Status", "name": "status", "control": "select", "options": number_status_options},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False},
                ],
            },
        },
        {
            "id": "channels",
            "label": "Channels",
            "description": "Voice, Chatwoot, webchat, WhatsApp and email entrypoints for this tenant.",
            "status": "live",
            "component": "crud-grid",
            "records": channel_records,
            "crud": {
                "title": "Channels",
                "description": "Tenant-owned customer entrypoints. Providers are mapped behind this Voxalia channel record.",
                "eyebrow": "channel",
                "createLabel": "Create channel",
                "createAction": f"/api/settings/tenants/{tenant_key}/channels",
                "rowActionBasePath": f"/api/settings/tenants/{tenant_key}/channels",
                "identityField": "id",
                "titleField": "display_name",
                "searchPlaceholder": "Search channel, provider, routing key or language",
                "emptyTitle": "No channels match the current filters",
                "emptyDescription": "Create voice, Chatwoot, webchat, WhatsApp or email entrypoints for this tenant.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "channel_type", "label": "Type", "allLabel": "All channel types", "options": channel_type_options},
                    {"key": "provider", "label": "Provider", "allLabel": "All providers", "options": provider_options},
                    {"key": "status", "label": "Status", "allLabel": "All statuses", "options": channel_status_options},
                ],
                "columns": [
                    {"id": "display_name", "header": "Channel"},
                    {"id": "channel_type", "header": "Type"},
                    {"id": "provider", "header": "Provider"},
                    {"id": "external_key", "header": "External key"},
                    {"id": "service_policy", "header": "Policy"},
                    {"id": "default_language", "header": "Language"},
                    {"id": "recording_required", "header": "Recording"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"label": "Channel key", "name": "channel_key", "placeholder": "main-toll-free"},
                    {"label": "Display name", "name": "display_name", "placeholder": "Main toll-free"},
                    {"label": "Type", "name": "channel_type", "control": "select", "options": channel_type_options, "defaultValue": "voice_toll_free"},
                    {"label": "Provider", "name": "provider", "control": "select", "options": provider_options, "defaultValue": "asterisk"},
                    {"label": "External key", "name": "routing_key", "required": False, "placeholder": "chatwoot inbox id, WhatsApp phone id or webchat widget key", "hideWhen": {"field": "channel_type", "values": ["voice_toll_free", "voice_local"]}},
                    {"label": "Service policy", "name": "service_policy_id", "control": "select", "options": policy_options, "required": False},
                    {"label": "Default language", "name": "default_language", "control": "select", "options": language_options, "defaultValue": "en"},
                    {"label": "Recording required", "name": "recording_required", "control": "select", "options": boolean_options, "defaultValue": "true"},
                    {"label": "Status", "name": "status", "control": "select", "options": channel_status_options, "defaultValue": "active"},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"label": "Channel key", "name": "channel_key"},
                    {"label": "Display name", "name": "display_name"},
                    {"label": "Type", "name": "channel_type", "control": "select", "options": channel_type_options},
                    {"label": "Provider", "name": "provider", "control": "select", "options": provider_options},
                    {"label": "External key", "name": "routing_key", "required": False, "hideWhen": {"field": "channel_type", "values": ["voice_toll_free", "voice_local"]}},
                    {"label": "Service policy", "name": "service_policy_id", "control": "select", "options": policy_options, "required": False},
                    {"label": "Default language", "name": "default_language", "control": "select", "options": language_options},
                    {"label": "Recording required", "name": "recording_required", "control": "select", "options": boolean_options},
                    {"label": "Status", "name": "status", "control": "select", "options": channel_status_options},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False},
                ],
            },
        },
        {
            "id": "contacts",
            "label": "Contacts",
            "description": "Escalation, reservation, operations, billing and reporting contacts.",
            "status": "live",
            "component": "crud-grid",
            "records": contact_records,
            "crud": {
                "title": "Contacts",
                "description": "People, departments and functional contacts for this tenant. Contact methods are managed from each contact row.",
                "eyebrow": "contact",
                "createLabel": "Create contact",
                "createAction": f"/api/settings/tenants/{tenant_key}/contacts",
                "rowActionBasePath": f"/api/settings/tenants/{tenant_key}/contacts",
                "identityField": "id",
                "titleField": "display_name",
                "searchPlaceholder": "Search contact, department, title or notes",
                "emptyTitle": "No contacts match the current filters",
                "emptyDescription": "Create the hotel contacts used for escalations, reporting and operational follow-up.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "contact_type", "label": "Type", "allLabel": "All contact types", "options": contact_type_options},
                    {"key": "status", "label": "Status", "allLabel": "All statuses", "options": contact_status_options},
                ],
                "columns": [
                    {"id": "display_name", "header": "Contact"},
                    {"id": "contact_type", "header": "Type"},
                    {"id": "department", "header": "Department"},
                    {"id": "title", "header": "Title"},
                    {"id": "priority", "header": "Priority"},
                    {"id": "methods", "header": "Methods"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"label": "Display name", "name": "display_name", "placeholder": "Front Desk"},
                    {"label": "Organization", "name": "organization", "required": False, "placeholder": "Hotel Valle Azul"},
                    {"label": "Department", "name": "department", "required": False, "placeholder": "Reservations"},
                    {"label": "Title", "name": "title", "required": False, "placeholder": "Reservations Manager"},
                    {"label": "Type", "name": "contact_type", "control": "select", "options": contact_type_options, "defaultValue": "operations"},
                    {"label": "Priority", "name": "priority", "type": "number", "defaultValue": "100"},
                    {"label": "Status", "name": "status", "control": "select", "options": contact_status_options, "defaultValue": "active"},
                    {"label": "Notes", "name": "notes", "control": "textarea", "required": False},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"label": "Display name", "name": "display_name"},
                    {"label": "Organization", "name": "organization", "required": False},
                    {"label": "Department", "name": "department", "required": False},
                    {"label": "Title", "name": "title", "required": False},
                    {"label": "Type", "name": "contact_type", "control": "select", "options": contact_type_options},
                    {"label": "Priority", "name": "priority", "type": "number"},
                    {"label": "Status", "name": "status", "control": "select", "options": contact_status_options},
                    {"label": "Notes", "name": "notes", "control": "textarea", "required": False},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False},
                ],
            },
        },
        {
            "id": "contact-methods",
            "label": "Contact Methods",
            "description": "Phones, emails, WhatsApp numbers, SMS numbers and extensions for a selected contact.",
            "status": "live",
            "component": "crud-grid",
            "hiddenFromTabs": True,
            "parentSectionId": "contacts",
            "records": contact_method_records,
            "crud": {
                "title": "Contact Methods",
                "description": "Ways to reach the selected tenant contact.",
                "eyebrow": "contact method",
                "createLabel": "Create method",
                "createAction": f"/api/settings/tenants/{tenant_key}/contact-methods",
                "rowActionBasePath": f"/api/settings/tenants/{tenant_key}/contact-methods",
                "identityField": "id",
                "titleField": "value",
                "searchPlaceholder": "Search method, value, contact or availability",
                "emptyTitle": "No contact methods match the current filters",
                "emptyDescription": "Add phones, emails, WhatsApp numbers or extensions for the selected contact.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "method_type", "label": "Method", "allLabel": "All method types", "options": contact_method_type_options},
                ],
                "columns": [
                    {"id": "method_type", "header": "Method"},
                    {"id": "label", "header": "Label"},
                    {"id": "value", "header": "Value"},
                    {"id": "availability", "header": "Availability"},
                ],
                "createFields": [
                    {"label": "Contact", "name": "contact_id", "control": "select", "options": contact_options},
                    {"label": "Method type", "name": "method_type", "control": "select", "options": contact_method_type_options, "defaultValue": "phone"},
                    {"label": "Label", "name": "label", "required": False, "placeholder": "Mobile, office, after hours"},
                    {"label": "Value", "name": "value", "placeholder": "+50640001001 or manager@example.com"},
                    {"label": "Primary", "name": "is_primary", "control": "select", "options": boolean_options, "defaultValue": "false"},
                    {"label": "Can receive escalations", "name": "can_receive_escalations", "control": "select", "options": boolean_options, "defaultValue": "false"},
                    {"label": "Availability", "name": "availability", "required": False, "placeholder": "24/7, business hours, after hours"},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"label": "Contact", "name": "contact_id", "control": "select", "options": contact_options},
                    {"label": "Method type", "name": "method_type", "control": "select", "options": contact_method_type_options},
                    {"label": "Label", "name": "label", "required": False},
                    {"label": "Value", "name": "value"},
                    {"label": "Primary", "name": "is_primary", "control": "select", "options": boolean_options},
                    {"label": "Can receive escalations", "name": "can_receive_escalations", "control": "select", "options": boolean_options},
                    {"label": "Availability", "name": "availability", "required": False},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False},
                ],
            },
        },
        {
            "id": "agents",
            "label": "Agents",
            "description": "Voxalia operators, skills, languages and tenant assignment rules.",
            "status": "placeholder",
            "component": "crud-grid",
            "records": [],
        },
        {
            "id": "service-policy",
            "label": "Service Policy",
            "description": "Hours, languages, after-hours behavior, escalation rules and callback windows.",
            "status": "placeholder",
            "component": "policy-editor",
            "records": [],
        },
        {
            "id": "scripts",
            "label": "Scripts",
            "description": "Disclosure text, intake guidance and tenant-specific call handling instructions.",
            "status": "placeholder",
            "component": "crud-grid",
            "records": [],
        },
        {
            "id": "reporting",
            "label": "Reporting",
            "description": "Report recipients, delivery rules, retention policy and management summaries.",
            "status": "placeholder",
            "component": "crud-grid",
            "records": [],
        },
        {
            "id": "audit",
            "label": "Audit",
            "description": "Tenant-scoped security and operational changes.",
            "status": "placeholder",
            "component": "audit-log",
            "records": [],
        },
    ]

    return {
        "workspace": {
            "id": "settings.tenants.detail",
            "title": "Tenant Workspace",
            "status": "Live",
        },
        "subject": {
            "id": tenant["id_text"],
            "key": tenant["tenant_key"],
            "title": tenant["display_name"],
            "subtitle": tenant["legal_name"] or f"{tenant['vertical']} tenant",
            "status": tenant["status"],
            "badges": [tenant["vertical"], tenant["timezone"]],
        },
        "context": {"client_id": context.tenant_key, "role": context.role},
        "links": {},
        "actions": [],
        "summary": [
            {"label": "Users", "value": user_count, "tone": "blue"},
            {"label": "Products", "value": workspace_counts["products"], "tone": "green"},
            {"label": "Channels", "value": workspace_counts["channels"], "tone": "amber"},
            {"label": "Voice Numbers", "value": workspace_counts["numbers"], "tone": "amber"},
            {"label": "Contacts", "value": workspace_counts["contacts"], "tone": "blue"},
            {"label": "Agents", "value": workspace_counts["agents"], "tone": "red"},
            {"label": "Scripts", "value": workspace_counts["scripts"], "tone": "green"},
            {"label": "Reports", "value": workspace_counts["reporting_recipients"], "tone": "blue"},
        ],
        "sections": sections,
    }


@app.get("/api/v1/settings/agents/{agent_id}/workspace")
def agent_workspace(agent_id: int, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    assignment_type_options = [
        {"value": "primary", "label": "Primary"},
        {"value": "backup", "label": "Backup"},
        {"value": "supervisor", "label": "Supervisor"},
        {"value": "specialist", "label": "Specialist"},
    ]
    assignment_status_options = [
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"},
    ]

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  ap.id::text,
                  ap.user_id::text,
                  u.display_name as user_name,
                  u.email as user_email,
                  ap.display_name,
                  array_to_string(ap.languages, ', ') as languages,
                  array_to_string(ap.skills, ', ') as skills,
                  ap.status,
                  coalesce(su.display_name, '') as supervisor,
                  coalesce(ap.supervisor_user_id::text, '') as supervisor_user_id,
                  ap.metadata,
                  ap.updated_at::text as updated_at
                from public.agent_profiles ap
                join public.auth_users u on u.id = ap.user_id
                left join public.auth_users su on su.id = ap.supervisor_user_id
                where ap.id = %(agent_id)s;
                """,
                {"agent_id": agent_id},
            )
            agent = cursor.fetchone()
            if not agent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
            agent_record = dict(agent)

            cursor.execute(
                """
                select
                  taa.id::text,
                  taa.tenant_id::text,
                  t.display_name as tenant,
                  t.tenant_key,
                  taa.assignment_type,
                  taa.queue_key,
                  taa.priority,
                  taa.status,
                  taa.metadata,
                  taa.updated_at::text
                from public.tenant_agent_assignments taa
                join public.tenants t on t.id = taa.tenant_id
                where taa.agent_profile_id = %(agent_id)s
                order by taa.status asc, taa.priority asc, t.display_name asc, taa.id asc;
                """,
                {"agent_id": agent_id},
            )
            assignment_records = [dict(row) for row in cursor.fetchall()]
            tenants = tenant_options(cursor)
            cursor.execute(
                """
                select
                  aea.id::text,
                  aea.tenant_id::text,
                  t.display_name as tenant,
                  t.tenant_key,
                  aea.logical_extension_id::text,
                  le.logical_extension,
                  le.display_name as extension_name,
                  le.provider_endpoint,
                  le.status as extension_status,
                  count(ed.id)::int as devices,
                  aea.status,
                  aea.metadata,
                  aea.updated_at::text
                from asterisk.agent_extension_assignments aea
                join public.tenants t on t.id = aea.tenant_id
                join asterisk.logical_extensions le
                  on le.id = aea.logical_extension_id
                 and le.tenant_id = aea.tenant_id
                left join asterisk.extension_devices ed
                  on ed.logical_extension_id = le.id
                 and ed.tenant_id = le.tenant_id
                 and ed.status = 'active'
                where aea.agent_profile_id = %(agent_id)s
                group by aea.id, aea.tenant_id, t.display_name, t.tenant_key,
                         aea.logical_extension_id, le.logical_extension, le.display_name,
                         le.provider_endpoint, le.status, aea.status, aea.metadata, aea.updated_at
                order by t.display_name asc, le.logical_extension asc, aea.id asc;
                """,
                {"agent_id": agent_id},
            )
            telephony_records = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                select distinct
                  le.id::text as value,
                  le.tenant_id::text as tenant_id,
                  t.display_name || ' - ' || le.logical_extension || ' - ' || le.display_name as label
                from asterisk.logical_extensions le
                join public.tenants t on t.id = le.tenant_id
                join public.tenant_agent_assignments taa
                  on taa.tenant_id = le.tenant_id
                 and taa.agent_profile_id = %(agent_id)s
                 and taa.status = 'active'
                where le.status in ('active', 'provisioning')
                  and le.extension_type in ('agent', 'supervisor', 'test')
                order by label asc;
                """,
                {"agent_id": agent_id},
            )
            extension_options = [dict(row) for row in cursor.fetchall()]

    active_assignments = [row for row in assignment_records if row["status"] == "active"]
    active_telephony = [row for row in telephony_records if row["status"] == "active"]
    telephony_status_options = [
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"},
        {"value": "provisioning", "label": "Provisioning"},
        {"value": "failed", "label": "Failed"},
    ]
    sections = [
        {
            "id": "overview",
            "label": "Overview",
            "description": "Agent identity, operational status, languages and skills.",
            "status": "live",
            "component": "details",
            "records": [agent_record],
        },
        {
            "id": "tenant-assignments",
            "label": "Tenant Assignments",
            "description": "Tenants and queues this Voxalia agent can serve.",
            "status": "live",
            "component": "crud-grid",
            "records": assignment_records,
            "crud": {
                "title": "Tenant Assignments",
                "description": "Map this agent to one or more tenant service responsibilities.",
                "eyebrow": "assignment",
                "createLabel": "Create assignment",
                "createAction": f"/api/settings/agents/{agent_id}/tenant-assignments",
                "rowActionBasePath": f"/api/settings/agents/{agent_id}/tenant-assignments",
                "identityField": "id",
                "titleField": "tenant",
                "searchPlaceholder": "Search tenant, queue or assignment type",
                "emptyTitle": "No tenant assignments match the current filters",
                "emptyDescription": "Assign this agent to one or more tenants or queues.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "assignment_type", "label": "Type", "allLabel": "All assignment types", "options": assignment_type_options},
                    {"key": "status", "label": "Status", "allLabel": "All statuses", "options": assignment_status_options},
                ],
                "columns": [
                    {"id": "tenant", "header": "Tenant"},
                    {"id": "assignment_type", "header": "Type"},
                    {"id": "queue_key", "header": "Queue"},
                    {"id": "priority", "header": "Priority"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"label": "Tenant", "name": "tenant_id", "control": "select", "options": tenants},
                    {"label": "Assignment type", "name": "assignment_type", "control": "select", "options": assignment_type_options, "defaultValue": "primary"},
                    {"label": "Queue key", "name": "queue_key", "required": False, "placeholder": "Optional until queue catalog is finalized"},
                    {"label": "Priority", "name": "priority", "type": "number", "defaultValue": "100"},
                    {"label": "Status", "name": "status", "control": "select", "options": assignment_status_options, "defaultValue": "active"},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"label": "Tenant", "name": "tenant_id", "control": "select", "options": tenants},
                    {"label": "Assignment type", "name": "assignment_type", "control": "select", "options": assignment_type_options},
                    {"label": "Queue key", "name": "queue_key", "required": False},
                    {"label": "Priority", "name": "priority", "type": "number"},
                    {"label": "Status", "name": "status", "control": "select", "options": assignment_status_options},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False},
                ],
            },
        },
        {
            "id": "telephony",
            "label": "Telephony",
            "description": "Tenant extension identities assigned to this agent.",
            "status": "live",
            "component": "crud-grid",
            "hiddenFromTabs": True,
            "parentSectionId": "tenant-assignments",
            "records": telephony_records,
            "crud": {
                "title": "Agent Extension Assignments",
                "description": "Map this agent to tenant-scoped Asterisk logical extensions.",
                "eyebrow": "extension assignment",
                "createLabel": "Assign extension",
                "createAction": f"/api/settings/agents/{agent_id}/extension-assignments",
                "rowActionBasePath": f"/api/settings/agents/{agent_id}/extension-assignments",
                "identityField": "id",
                "titleField": "logical_extension",
                "searchPlaceholder": "Search tenant, extension, endpoint or status",
                "emptyTitle": "No extension assignments match the current filters",
                "emptyDescription": "Create an active tenant assignment first, then assign this agent to a tenant extension.",
                "allowedActions": ["view", "edit", "delete"],
                "filters": [
                    {"key": "status", "label": "Status", "allLabel": "All statuses", "options": telephony_status_options},
                ],
                "columns": [
                    {"id": "logical_extension", "header": "Extension"},
                    {"id": "extension_name", "header": "Name"},
                    {"id": "provider_endpoint", "header": "Endpoint"},
                    {"id": "devices", "header": "Devices"},
                    {"id": "status", "header": "Status"},
                ],
                "createFields": [
                    {"label": "Tenant", "name": "tenant_id", "control": "select", "options": tenants},
                    {"label": "Extension", "name": "logical_extension_id", "control": "select", "options": extension_options},
                    {"label": "Status", "name": "status", "control": "select", "options": telephony_status_options, "defaultValue": "active"},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False, "defaultValue": "{}"},
                ],
                "editFields": [
                    {"label": "Tenant", "name": "tenant_id", "control": "select", "options": tenants},
                    {"label": "Extension", "name": "logical_extension_id", "control": "select", "options": extension_options},
                    {"label": "Status", "name": "status", "control": "select", "options": telephony_status_options},
                    {"label": "Metadata JSON", "name": "metadata", "control": "json", "required": False},
                ],
            },
        },
        {
            "id": "availability",
            "label": "Availability",
            "description": "Future status history, breaks, schedules and real-time presence.",
            "status": "placeholder",
            "component": "crud-grid",
            "records": [],
        },
    ]

    return {
        "workspace": {
            "id": "settings.agents.detail",
            "title": "Agent Workspace",
            "status": "Live",
        },
        "subject": {
            "id": agent_record["id"],
            "key": agent_record["id"],
            "title": agent_record["display_name"],
            "subtitle": agent_record["user_email"],
            "status": agent_record["status"],
            "badges": [agent_record["languages"], agent_record["skills"]],
        },
        "context": {"client_id": context.tenant_key, "role": context.role},
        "links": {},
        "actions": [],
        "summary": [
            {"label": "Active Assignments", "value": len(active_assignments), "tone": "blue"},
            {"label": "Total Assignments", "value": len(assignment_records), "tone": "green"},
            {"label": "Active Extensions", "value": len(active_telephony), "tone": "blue"},
            {"label": "Languages", "value": len(normalize_text_list(agent_record["languages"])), "tone": "amber"},
            {"label": "Skills", "value": len(normalize_text_list(agent_record["skills"])), "tone": "red"},
        ],
        "sections": sections,
    }


@app.post("/api/v1/settings/agents/{agent_id}/tenant-assignments", status_code=201)
def create_agent_assignment(agent_id: int, payload: TenantAgentAssignmentRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.agent_profiles where id = %(agent_id)s;", {"agent_id": agent_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
            cursor.execute("select id from public.tenants where id = %(tenant_id)s;", {"tenant_id": payload.tenant_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown tenant")

            cursor.execute(
                """
                insert into public.tenant_agent_assignments (
                  tenant_id, agent_profile_id, assignment_type, queue_key, priority, status, metadata
                )
                values (
                  %(tenant_id)s, %(agent_id)s, %(assignment_type)s, %(queue_key)s, %(priority)s, %(status)s, %(metadata)s::jsonb
                )
                returning id::text, tenant_id::text, agent_profile_id::text, assignment_type, queue_key, priority, status, metadata;
                """,
                {
                    "tenant_id": payload.tenant_id,
                    "agent_id": agent_id,
                    "assignment_type": payload.assignment_type,
                    "queue_key": payload.queue_key,
                    "priority": payload.priority,
                    "status": payload.status,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            assignment = dict(cursor.fetchone())
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.assignment.create', 'tenant_agent_assignment', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": payload.tenant_id, "subject_id": assignment["id"]},
            )
            connection.commit()

    return assignment


@app.patch("/api/v1/settings/agents/{agent_id}/tenant-assignments/{assignment_id}")
def update_agent_assignment(agent_id: int, assignment_id: int, payload: TenantAgentAssignmentRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.tenants where id = %(tenant_id)s;", {"tenant_id": payload.tenant_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown tenant")

            cursor.execute(
                """
                update public.tenant_agent_assignments
                set
                  tenant_id = %(tenant_id)s,
                  assignment_type = %(assignment_type)s,
                  queue_key = %(queue_key)s,
                  priority = %(priority)s,
                  status = %(status)s,
                  metadata = %(metadata)s::jsonb,
                  updated_at = now()
                where id = %(assignment_id)s
                  and agent_profile_id = %(agent_id)s
                returning id::text, tenant_id::text, agent_profile_id::text, assignment_type, queue_key, priority, status, metadata;
                """,
                {
                    "assignment_id": assignment_id,
                    "agent_id": agent_id,
                    "tenant_id": payload.tenant_id,
                    "assignment_type": payload.assignment_type,
                    "queue_key": payload.queue_key,
                    "priority": payload.priority,
                    "status": payload.status,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            assignment = cursor.fetchone()
            if not assignment:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.assignment.update', 'tenant_agent_assignment', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": payload.tenant_id, "subject_id": str(assignment_id)},
            )
            connection.commit()

    return dict(assignment)


@app.delete("/api/v1/settings/agents/{agent_id}/tenant-assignments/{assignment_id}")
def delete_agent_assignment(agent_id: int, assignment_id: int, context: RequestContext = Depends(require_context)) -> dict[str, str]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from public.tenant_agent_assignments
                where id = %(assignment_id)s
                  and agent_profile_id = %(agent_id)s
                returning id::text, tenant_id;
                """,
                {"assignment_id": assignment_id, "agent_id": agent_id},
            )
            deleted = cursor.fetchone()
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.assignment.delete', 'tenant_agent_assignment', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": deleted["tenant_id"], "subject_id": deleted["id"]},
            )
            connection.commit()

    return {"status": "deleted", "id": deleted["id"]}


@app.post("/api/v1/settings/agents/{agent_id}/extension-assignments", status_code=201)
def create_agent_extension_assignment(agent_id: int, payload: AgentExtensionAssignmentRequest, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id from public.agent_profiles where id = %(agent_id)s;", {"agent_id": agent_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
            cursor.execute(
                """
                select id
                from public.tenant_agent_assignments
                where agent_profile_id = %(agent_id)s
                  and tenant_id = %(tenant_id)s
                  and status = 'active';
                """,
                {"agent_id": agent_id, "tenant_id": payload.tenant_id},
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent is not actively assigned to this tenant")
            cursor.execute(
                """
                select id
                from asterisk.logical_extensions
                where id = %(extension_id)s
                  and tenant_id = %(tenant_id)s;
                """,
                {"extension_id": payload.logical_extension_id, "tenant_id": payload.tenant_id},
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown extension for tenant")
            if payload.status == "active":
                cursor.execute(
                    """
                    select id
                    from asterisk.agent_extension_assignments
                    where agent_profile_id = %(agent_id)s
                      and tenant_id = %(tenant_id)s
                      and status = 'active';
                    """,
                    {"agent_id": agent_id, "tenant_id": payload.tenant_id},
                )
                if cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent already has an active extension for this tenant")

            cursor.execute(
                """
                insert into asterisk.agent_extension_assignments (
                  tenant_id, agent_profile_id, logical_extension_id, status, metadata
                )
                values (
                  %(tenant_id)s, %(agent_id)s, %(extension_id)s, %(status)s, %(metadata)s::jsonb
                )
                returning id::text, tenant_id::text, agent_profile_id::text, logical_extension_id::text, status, metadata;
                """,
                {
                    "tenant_id": payload.tenant_id,
                    "agent_id": agent_id,
                    "extension_id": payload.logical_extension_id,
                    "status": payload.status,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            assignment = dict(cursor.fetchone())
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.extension_assignment.create', 'agent_extension_assignment', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": payload.tenant_id, "subject_id": assignment["id"]},
            )
            connection.commit()

    return assignment


@app.patch("/api/v1/settings/agents/{agent_id}/extension-assignments/{assignment_id}")
def update_agent_extension_assignment(
    agent_id: int,
    assignment_id: int,
    payload: AgentExtensionAssignmentRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id
                from public.tenant_agent_assignments
                where agent_profile_id = %(agent_id)s
                  and tenant_id = %(tenant_id)s
                  and status = 'active';
                """,
                {"agent_id": agent_id, "tenant_id": payload.tenant_id},
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent is not actively assigned to this tenant")
            cursor.execute(
                """
                select id
                from asterisk.logical_extensions
                where id = %(extension_id)s
                  and tenant_id = %(tenant_id)s;
                """,
                {"extension_id": payload.logical_extension_id, "tenant_id": payload.tenant_id},
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown extension for tenant")
            if payload.status == "active":
                cursor.execute(
                    """
                    select id
                    from asterisk.agent_extension_assignments
                    where agent_profile_id = %(agent_id)s
                      and tenant_id = %(tenant_id)s
                      and status = 'active'
                      and id <> %(assignment_id)s;
                    """,
                    {"agent_id": agent_id, "tenant_id": payload.tenant_id, "assignment_id": assignment_id},
                )
                if cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent already has an active extension for this tenant")

            cursor.execute(
                """
                update asterisk.agent_extension_assignments
                set
                  tenant_id = %(tenant_id)s,
                  logical_extension_id = %(extension_id)s,
                  status = %(status)s,
                  metadata = %(metadata)s::jsonb,
                  updated_at = now()
                where id = %(assignment_id)s
                  and agent_profile_id = %(agent_id)s
                returning id::text, tenant_id::text, agent_profile_id::text, logical_extension_id::text, status, metadata;
                """,
                {
                    "assignment_id": assignment_id,
                    "agent_id": agent_id,
                    "tenant_id": payload.tenant_id,
                    "extension_id": payload.logical_extension_id,
                    "status": payload.status,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            assignment = cursor.fetchone()
            if not assignment:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension assignment not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.extension_assignment.update', 'agent_extension_assignment', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": payload.tenant_id, "subject_id": str(assignment_id)},
            )
            connection.commit()

    return dict(assignment)


@app.delete("/api/v1/settings/agents/{agent_id}/extension-assignments/{assignment_id}")
def delete_agent_extension_assignment(agent_id: int, assignment_id: int, context: RequestContext = Depends(require_context)) -> dict[str, str]:
    require_permission(context, "auth:users:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from asterisk.agent_extension_assignments
                where id = %(assignment_id)s
                  and agent_profile_id = %(agent_id)s
                returning id::text, tenant_id;
                """,
                {"assignment_id": assignment_id, "agent_id": agent_id},
            )
            deleted = cursor.fetchone()
            if not deleted:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension assignment not found")

            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'agent.extension_assignment.delete', 'agent_extension_assignment', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": deleted["tenant_id"], "subject_id": deleted["id"]},
            )
            connection.commit()

    return {"status": "deleted", "id": deleted["id"]}


@app.post("/api/v1/settings/tenants/{tenant_key}/channels", status_code=201)
def create_tenant_channel(
    tenant_key: str,
    payload: TenantChannelRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            ensure_service_policy(cursor, tenant["id"], payload.service_policy_id)
            cursor.execute(
                """
                insert into public.tenant_channels (
                  tenant_id, service_policy_id, channel_key, channel_type, display_name,
                  provider, routing_key, default_language, status, recording_required, metadata
                )
                values (
                  %(tenant_id)s, %(service_policy_id)s, %(channel_key)s, %(channel_type)s, %(display_name)s,
                  %(provider)s, %(routing_key)s, %(default_language)s, %(status)s, %(recording_required)s, %(metadata)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "service_policy_id": payload.service_policy_id,
                    "channel_key": payload.channel_key,
                    "channel_type": payload.channel_type,
                    "display_name": payload.display_name,
                    "provider": payload.provider,
                    "routing_key": payload.routing_key,
                    "default_language": payload.default_language,
                    "status": payload.status,
                    "recording_required": payload.recording_required,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            channel = cursor.fetchone()
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.channel.create', 'tenant_channel', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": channel["id"]},
            )
            connection.commit()
    return {"id": channel["id"], "status": "created"}


@app.patch("/api/v1/settings/tenants/{tenant_key}/channels/{channel_id}")
def update_tenant_channel(
    tenant_key: str,
    channel_id: int,
    payload: TenantChannelRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            ensure_service_policy(cursor, tenant["id"], payload.service_policy_id)
            cursor.execute(
                """
                update public.tenant_channels
                set
                  service_policy_id = %(service_policy_id)s,
                  channel_key = %(channel_key)s,
                  channel_type = %(channel_type)s,
                  display_name = %(display_name)s,
                  provider = %(provider)s,
                  routing_key = %(routing_key)s,
                  default_language = %(default_language)s,
                  status = %(status)s,
                  recording_required = %(recording_required)s,
                  metadata = %(metadata)s::jsonb,
                  updated_at = now()
                where id = %(channel_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "channel_id": channel_id,
                    "service_policy_id": payload.service_policy_id,
                    "channel_key": payload.channel_key,
                    "channel_type": payload.channel_type,
                    "display_name": payload.display_name,
                    "provider": payload.provider,
                    "routing_key": payload.routing_key,
                    "default_language": payload.default_language,
                    "status": payload.status,
                    "recording_required": payload.recording_required,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            channel = cursor.fetchone()
            if not channel:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.channel.update', 'tenant_channel', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": channel["id"]},
            )
            connection.commit()
    return {"id": channel["id"], "status": "updated"}


@app.delete("/api/v1/settings/tenants/{tenant_key}/channels/{channel_id}")
def delete_tenant_channel(
    tenant_key: str,
    channel_id: int,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from public.tenant_channels
                where id = %(channel_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"tenant_id": tenant["id"], "channel_id": channel_id},
            )
            channel = cursor.fetchone()
            if not channel:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.channel.delete', 'tenant_channel', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": channel["id"]},
            )
            connection.commit()
    return {"id": channel["id"], "status": "deleted"}


@app.post("/api/v1/settings/tenants/{tenant_key}/numbers", status_code=201)
def create_voice_number(
    tenant_key: str,
    payload: VoiceNumberRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            ensure_tenant_channel(cursor, tenant["id"], payload.channel_id)
            country_code = ensure_country_code(cursor, payload.country_code)
            cursor.execute(
                """
                insert into public.voice_numbers (
                  tenant_id, channel_id, number_e164, label, number_type, country_code,
                  status, recording_required, metadata
                )
                values (
                  %(tenant_id)s, %(channel_id)s, %(number_e164)s, %(label)s, %(number_type)s, %(country_code)s,
                  %(status)s, %(recording_required)s, %(metadata)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "channel_id": payload.channel_id,
                    "number_e164": payload.number_e164,
                    "label": payload.label,
                    "number_type": payload.number_type,
                    "country_code": country_code,
                    "status": payload.status,
                    "recording_required": payload.recording_required,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            number = cursor.fetchone()
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.voice_number.create', 'voice_number', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": number["id"]},
            )
            connection.commit()
    return {"id": number["id"], "status": "created"}


@app.patch("/api/v1/settings/tenants/{tenant_key}/numbers/{number_id}")
def update_voice_number(
    tenant_key: str,
    number_id: int,
    payload: VoiceNumberRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            ensure_tenant_channel(cursor, tenant["id"], payload.channel_id)
            country_code = ensure_country_code(cursor, payload.country_code)
            cursor.execute(
                """
                update public.voice_numbers
                set
                  channel_id = %(channel_id)s,
                  number_e164 = %(number_e164)s,
                  label = %(label)s,
                  number_type = %(number_type)s,
                  country_code = %(country_code)s,
                  status = %(status)s,
                  recording_required = %(recording_required)s,
                  metadata = %(metadata)s::jsonb,
                  updated_at = now()
                where id = %(number_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "number_id": number_id,
                    "channel_id": payload.channel_id,
                    "number_e164": payload.number_e164,
                    "label": payload.label,
                    "number_type": payload.number_type,
                    "country_code": country_code,
                    "status": payload.status,
                    "recording_required": payload.recording_required,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            number = cursor.fetchone()
            if not number:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Number not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.voice_number.update', 'voice_number', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": number["id"]},
            )
            connection.commit()
    return {"id": number["id"], "status": "updated"}


@app.delete("/api/v1/settings/tenants/{tenant_key}/numbers/{number_id}")
def delete_voice_number(
    tenant_key: str,
    number_id: int,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from public.voice_numbers
                where id = %(number_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"tenant_id": tenant["id"], "number_id": number_id},
            )
            number = cursor.fetchone()
            if not number:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Number not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.voice_number.delete', 'voice_number', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": number["id"]},
            )
            connection.commit()
    return {"id": number["id"], "status": "deleted"}


@app.post("/api/v1/settings/tenants/{tenant_key}/contacts", status_code=201)
def create_tenant_contact(
    tenant_key: str,
    payload: TenantContactRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            cursor.execute(
                """
                insert into public.tenant_contacts (
                  tenant_id, display_name, organization, department, title,
                  contact_type, priority, status, notes, metadata
                )
                values (
                  %(tenant_id)s, %(display_name)s, %(organization)s, %(department)s, %(title)s,
                  %(contact_type)s, %(priority)s, %(status)s, %(notes)s, %(metadata)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "display_name": payload.display_name,
                    "organization": payload.organization,
                    "department": payload.department,
                    "title": payload.title,
                    "contact_type": payload.contact_type,
                    "priority": payload.priority,
                    "status": payload.status,
                    "notes": payload.notes,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            contact = cursor.fetchone()
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.contact.create', 'tenant_contact', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": contact["id"]},
            )
            connection.commit()
    return {"id": contact["id"], "status": "created"}


@app.patch("/api/v1/settings/tenants/{tenant_key}/contacts/{contact_id}")
def update_tenant_contact(
    tenant_key: str,
    contact_id: int,
    payload: TenantContactRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            cursor.execute(
                """
                update public.tenant_contacts
                set
                  display_name = %(display_name)s,
                  organization = %(organization)s,
                  department = %(department)s,
                  title = %(title)s,
                  contact_type = %(contact_type)s,
                  priority = %(priority)s,
                  status = %(status)s,
                  notes = %(notes)s,
                  metadata = %(metadata)s::jsonb,
                  updated_at = now()
                where id = %(contact_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "contact_id": contact_id,
                    "display_name": payload.display_name,
                    "organization": payload.organization,
                    "department": payload.department,
                    "title": payload.title,
                    "contact_type": payload.contact_type,
                    "priority": payload.priority,
                    "status": payload.status,
                    "notes": payload.notes,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            contact = cursor.fetchone()
            if not contact:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.contact.update', 'tenant_contact', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": contact["id"]},
            )
            connection.commit()
    return {"id": contact["id"], "status": "updated"}


@app.delete("/api/v1/settings/tenants/{tenant_key}/contacts/{contact_id}")
def delete_tenant_contact(
    tenant_key: str,
    contact_id: int,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from public.tenant_contacts
                where id = %(contact_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"tenant_id": tenant["id"], "contact_id": contact_id},
            )
            contact = cursor.fetchone()
            if not contact:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.contact.delete', 'tenant_contact', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": contact["id"]},
            )
            connection.commit()
    return {"id": contact["id"], "status": "deleted"}


@app.post("/api/v1/settings/tenants/{tenant_key}/contact-methods", status_code=201)
def create_tenant_contact_method(
    tenant_key: str,
    payload: TenantContactMethodRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            ensure_tenant_contact(cursor, tenant["id"], payload.contact_id)
            cursor.execute(
                """
                insert into public.tenant_contact_methods (
                  tenant_id, contact_id, method_type, label, value,
                  is_primary, can_receive_escalations, availability, metadata
                )
                values (
                  %(tenant_id)s, %(contact_id)s, %(method_type)s, %(label)s, %(value)s,
                  %(is_primary)s, %(can_receive_escalations)s, %(availability)s, %(metadata)s::jsonb
                )
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "contact_id": payload.contact_id,
                    "method_type": payload.method_type,
                    "label": payload.label,
                    "value": payload.value,
                    "is_primary": payload.is_primary,
                    "can_receive_escalations": payload.can_receive_escalations,
                    "availability": payload.availability,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            contact_method = cursor.fetchone()
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.contact_method.create', 'tenant_contact_method', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": contact_method["id"]},
            )
            connection.commit()
    return {"id": contact_method["id"], "status": "created"}


@app.patch("/api/v1/settings/tenants/{tenant_key}/contact-methods/{method_id}")
def update_tenant_contact_method(
    tenant_key: str,
    method_id: int,
    payload: TenantContactMethodRequest,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            ensure_tenant_contact(cursor, tenant["id"], payload.contact_id)
            cursor.execute(
                """
                update public.tenant_contact_methods
                set
                  contact_id = %(contact_id)s,
                  method_type = %(method_type)s,
                  label = %(label)s,
                  value = %(value)s,
                  is_primary = %(is_primary)s,
                  can_receive_escalations = %(can_receive_escalations)s,
                  availability = %(availability)s,
                  metadata = %(metadata)s::jsonb,
                  updated_at = now()
                where id = %(method_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {
                    "tenant_id": tenant["id"],
                    "method_id": method_id,
                    "contact_id": payload.contact_id,
                    "method_type": payload.method_type,
                    "label": payload.label,
                    "value": payload.value,
                    "is_primary": payload.is_primary,
                    "can_receive_escalations": payload.can_receive_escalations,
                    "availability": payload.availability,
                    "metadata": json.dumps(payload.metadata),
                },
            )
            contact_method = cursor.fetchone()
            if not contact_method:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact method not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.contact_method.update', 'tenant_contact_method', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": contact_method["id"]},
            )
            connection.commit()
    return {"id": contact_method["id"], "status": "updated"}


@app.delete("/api/v1/settings/tenants/{tenant_key}/contact-methods/{method_id}")
def delete_tenant_contact_method(
    tenant_key: str,
    method_id: int,
    context: RequestContext = Depends(require_context),
) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            tenant = tenant_for_key(cursor, tenant_key)
            cursor.execute(
                """
                delete from public.tenant_contact_methods
                where id = %(method_id)s
                  and tenant_id = %(tenant_id)s
                returning id::text;
                """,
                {"tenant_id": tenant["id"], "method_id": method_id},
            )
            contact_method = cursor.fetchone()
            if not contact_method:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact method not found")
            cursor.execute(
                """
                insert into public.auth_audit_log (user_id, tenant_id, action, subject_type, subject_id, metadata)
                values (%(actor_id)s, %(tenant_id)s, 'tenant.contact_method.delete', 'tenant_contact_method', %(subject_id)s, '{}'::jsonb);
                """,
                {"actor_id": context.user_id, "tenant_id": tenant["id"], "subject_id": contact_method["id"]},
            )
            connection.commit()
    return {"id": contact_method["id"], "status": "deleted"}


@app.get("/api/v1/{group}/{module}")
def generic_module(group: str, module: str, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    path = f"/{group}/{module}"
    item = item_for_path(path)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    required_permission = item.get("required_permission")
    if required_permission:
        require_permission(context, required_permission)
    return {
        "module": {
            "id": path.strip("/").replace("/", "."),
            "title": item["label"],
            "description": item["description"],
            "status": "Pending",
        },
        "context": {"client_id": context.tenant_key, "role": context.role},
        "links": {},
        "actions": [],
        "records": [],
    }
