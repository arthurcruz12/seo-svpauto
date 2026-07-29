from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import os
import secrets
import smtplib
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .schemas import AccountProfile
from .store import (
    consume_rate_limit,
    create_company,
    create_user,
    delete_mfa_challenge,
    ensure_company,
    ensure_user,
    get_company,
    get_mfa_challenge,
    get_user_by_email,
    increment_mfa_attempt,
    save_mfa_challenge,
)


JWT_SECRET = os.getenv("SEO_JWT_SECRET", "dev-only-change-before-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("SEO_ACCESS_TOKEN_MINUTES", "30"))
MFA_TTL_SECONDS = 300
MFA_MAX_ATTEMPTS = 5

APP_ENV = os.getenv("SEO_ENV", "development").lower()
ADMIN_EMAIL = os.getenv("SEO_ADMIN_EMAIL", "admin@seo.local").lower()
ADMIN_PASSWORD = os.getenv("SEO_ADMIN_PASSWORD", "Seo-Admin-2026")
EXPOSE_DEV_MFA = os.getenv("SEO_EXPOSE_DEV_MFA", "0") == "1"
SMTP_HOST = os.getenv("SEO_SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SEO_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SEO_SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SEO_SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SEO_SMTP_FROM", SMTP_USERNAME)

if APP_ENV == "production":
    if JWT_SECRET == "dev-only-change-before-production":
        raise RuntimeError("SEO_JWT_SECRET obrigatório em produção.")
    if ADMIN_PASSWORD == "Seo-Admin-2026":
        raise RuntimeError("SEO_ADMIN_PASSWORD obrigatório em produção.")
    if EXPOSE_DEV_MFA:
        raise RuntimeError("SEO_EXPOSE_DEV_MFA não pode estar ativo em produção.")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

ROLE_PERMISSIONS = {
    "admin": ["*"],
    "client": [
        "billing:manage",
        "dashboard:read",
        "documents:write",
        "files:upload",
        "finance:read",
        "finance:write",
        "inventory:read",
        "inventory:write",
        "reports:export",
        "reconciliation:read",
        "reconciliation:write",
    ],
}
def enforce_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)
    if not consume_rate_limit(key, limit, cutoff.isoformat()):
        raise HTTPException(status_code=429, detail="Demasiadas tentativas. Aguarde antes de repetir.")

ensure_user(
    name=os.getenv("SEO_ADMIN_NAME", "Administrador SEO"),
    email=ADMIN_EMAIL,
    role="admin",
    company_id=ensure_company(os.getenv("SEO_DEFAULT_COMPANY_NAME", "SEO Empresa Demo"))["id"],
    password_hash=pwd_context.hash(ADMIN_PASSWORD),
)


def register_client(name: str, email: str, password: str, company_name: str | None = None) -> AccountProfile:
    normalized_email = email.lower()
    if get_user_by_email(normalized_email):
        raise ValueError("Conta já existente.")

    company = create_company(company_name or f"Empresa de {name.strip()}")
    user = create_user(
        name=name.strip(),
        email=normalized_email,
        role="client",
        company_id=company["id"],
        password_hash=pwd_context.hash(password),
    )
    return account_profile(user)


def authenticate_user(email: str, password: str) -> dict | None:
    user = get_user_by_email(email.lower())
    if not user or not pwd_context.verify(password, user["password_hash"]):
        return None
    return user


def account_profile(user: dict) -> AccountProfile:
    role = user["role"]
    company = get_company(user["company_id"]) or {"id": user["company_id"], "name": "Empresa"}
    return AccountProfile(
        id=user["id"],
        company_id=company["id"],
        company_name=company["name"],
        name=user["name"],
        email=user["email"],
        role=role,
        permissions=ROLE_PERMISSIONS.get(role, []),
    )


def create_mfa_challenge(email: str) -> tuple[str, str | None, str]:
    challenge_id = str(uuid4())
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=MFA_TTL_SECONDS)
    save_mfa_challenge(challenge_id, email, pwd_context.hash(code), expires_at.isoformat())
    delivery_hint = deliver_mfa_code(email, code)
    expose_local_code = APP_ENV != "production" and not SMTP_HOST
    return challenge_id, code if EXPOSE_DEV_MFA or expose_local_code else None, delivery_hint


def deliver_mfa_code(email: str, code: str) -> str:
    if SMTP_HOST and SMTP_FROM:
        message = EmailMessage()
        message["Subject"] = "Código de acesso SEO"
        message["From"] = SMTP_FROM
        message["To"] = email
        message.set_content(f"O seu código temporário do SEO é: {code}\n\nEste código expira em 5 minutos.")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
        return "Código temporário enviado para o email configurado."

    if APP_ENV == "production":
        raise RuntimeError("SMTP obrigatório para MFA em produção.")

    return "Código temporário criado no ambiente local."


def verify_mfa_challenge(challenge_id: str, code: str) -> dict | None:
    challenge = get_mfa_challenge(challenge_id)
    if not challenge:
        return None
    if datetime.now(timezone.utc) > datetime.fromisoformat(challenge["expires_at"]):
        delete_mfa_challenge(challenge_id)
        return None

    attempts = increment_mfa_attempt(challenge_id)
    if attempts > MFA_MAX_ATTEMPTS:
        delete_mfa_challenge(challenge_id)
        return None

    valid = pwd_context.verify(code, challenge["code_hash"])
    if not valid:
        return None

    delete_mfa_challenge(challenge_id)
    return get_user_by_email(challenge["email"])


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": subject.lower(), "exp": expires_at}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        subject = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.") from exc

    user = get_user_by_email(str(subject).lower())
    if not user:
        raise HTTPException(status_code=401, detail="Conta não encontrada.")
    return user


def require_permission(permission: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        permissions = ROLE_PERMISSIONS.get(user["role"], [])
        if "*" not in permissions and permission not in permissions:
            raise HTTPException(status_code=403, detail="Sem permissão para esta operação.")
        return user

    return dependency
