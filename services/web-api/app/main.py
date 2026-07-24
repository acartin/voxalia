from datetime import UTC

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
                  t.timezone,
                  t.status,
                  count(ut.user_id)::int as users,
                  t.updated_at::text as updated_at
                from public.tenants t
                left join public.auth_user_tenants ut on ut.tenant_id = t.id
                group by t.id, t.tenant_key, t.display_name, t.legal_name, t.vertical, t.timezone, t.status, t.updated_at
                order by t.display_name asc, t.id asc;
                """
            )
            records = [dict(row) for row in cursor.fetchall()]

    return {
        "module": {
            "id": "settings.tenants",
            "title": item["label"] if item else "Tenants",
            "description": item["description"] if item else "Partners, policies and tenant workspaces.",
            "status": "Live",
        },
        "context": {"client_id": context.tenant_key, "role": context.role},
        "links": {},
        "actions": [],
        "records": records,
    }


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


@app.get("/api/v1/settings/tenants/{tenant_key}/workspace")
def tenant_workspace(tenant_key: str, context: RequestContext = Depends(require_context)) -> dict[str, object]:
    require_permission(context, "tenants:manage")

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id, id::text as id_text, tenant_key, display_name, legal_name, vertical, timezone, status
                from public.tenants
                where tenant_key = %(tenant_key)s;
                """,
                {"tenant_key": tenant_key},
            )
            tenant = cursor.fetchone()
            if not tenant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

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
            "label": "Numbers & Routing",
            "description": "Toll-free numbers, local DIDs, inbound routes, queues and recording policy.",
            "status": "placeholder",
            "component": "crud-grid",
            "records": [],
        },
        {
            "id": "channels",
            "label": "Channels",
            "description": "Voice, Chatwoot, webchat, WhatsApp and email entrypoints for this tenant.",
            "status": "placeholder",
            "component": "crud-grid",
            "records": [],
        },
        {
            "id": "contacts",
            "label": "Contacts",
            "description": "Escalation, reservation, operations, billing and reporting contacts.",
            "status": "placeholder",
            "component": "crud-grid",
            "records": [],
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
            {"label": "Numbers", "value": workspace_counts["numbers"], "tone": "amber"},
            {"label": "Contacts", "value": workspace_counts["contacts"], "tone": "blue"},
            {"label": "Agents", "value": workspace_counts["agents"], "tone": "red"},
            {"label": "Scripts", "value": workspace_counts["scripts"], "tone": "green"},
            {"label": "Reports", "value": workspace_counts["reporting_recipients"], "tone": "blue"},
        ],
        "sections": sections,
    }


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
