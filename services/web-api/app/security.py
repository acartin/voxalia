import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Header, HTTPException, status

from app.db import db


@dataclass(frozen=True)
class RequestContext:
    token_hash: str
    user_id: int
    email: str
    role: str
    role_label: str
    tenant_id: int
    tenant_key: str
    tenant_name: str
    permissions: frozenset[str]
    can_simulate_roles: bool
    is_role_simulated: bool


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_token() -> str:
    return secrets.token_urlsafe(48)


def session_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(hours=12)


def make_password_hash(password: str) -> str:
    iterations = 260000
    salt = base64.urlsafe_b64encode(secrets.token_bytes(18)).decode("utf-8").rstrip("=")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    encoded = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return f"pbkdf2_sha256${iterations}${salt}${encoded}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
      algorithm, iterations_raw, salt, expected = password_hash.split("$", 3)
      iterations = int(iterations_raw)
    except ValueError:
      return False

    if algorithm != "pbkdf2_sha256":
      return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    actual = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return hmac.compare_digest(actual, expected)


def require_context(authorization: str | None = Header(default=None)) -> RequestContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")

    token_hash = hash_token(token)

    with db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                  u.id as user_id,
                  u.email,
                  coalesce(s.active_role_id, min(r.id)) as role,
                  coalesce(ar.label, min(r.label)) as role_label,
                  coalesce(s.active_tenant_id, min(t.id)) as tenant_id,
                  coalesce(at.tenant_key, min(t.tenant_key)) as tenant_key,
                  coalesce(at.display_name, min(t.display_name)) as tenant_name,
                  bool_or(ur.role_id = 'system_admin') as can_simulate_roles,
                  coalesce(s.active_role_id, min(r.id)) <> 'system_admin' and bool_or(ur.role_id = 'system_admin') as is_role_simulated
                from public.auth_sessions s
                join public.auth_users u on u.id = s.user_id
                join public.auth_user_roles ur on ur.user_id = u.id
                join public.auth_roles r on r.id = ur.role_id
                join public.auth_user_tenants ut on ut.user_id = u.id
                join public.tenants t on t.id = ut.tenant_id
                left join public.auth_roles ar on ar.id = s.active_role_id
                left join public.tenants at on at.id = s.active_tenant_id
                where s.session_token_hash = %(token_hash)s
                  and s.revoked_at is null
                  and s.expires_at > now()
                  and u.status = 'active'
                group by u.id, u.email, s.active_role_id, ar.label, s.active_tenant_id, at.tenant_key, at.display_name;
                """,
                {"token_hash": token_hash},
            )
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

            cursor.execute(
                """
                select permission_id
                from public.auth_role_permissions
                where role_id = %(role_id)s;
                """,
                {"role_id": session["role"]},
            )
            permissions = frozenset(str(row["permission_id"]) for row in cursor.fetchall())

            cursor.execute(
                """
                update public.auth_sessions
                set last_seen_at = now()
                where session_token_hash = %(token_hash)s;
                """,
                {"token_hash": token_hash},
            )
            connection.commit()

    return RequestContext(
        token_hash=token_hash,
        user_id=int(session["user_id"]),
        email=str(session["email"]),
        role=str(session["role"]),
        role_label=str(session["role_label"]),
        tenant_id=int(session["tenant_id"]),
        tenant_key=str(session["tenant_key"]),
        tenant_name=str(session["tenant_name"]),
        permissions=permissions,
        can_simulate_roles=bool(session["can_simulate_roles"]),
        is_role_simulated=bool(session["is_role_simulated"]),
    )


def require_permission(context: RequestContext, permission: str) -> None:
    if permission not in context.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
