from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest
from pydantic import BaseModel, Field

from .audit import record_audit_event
from .password_security import update_password_hash, validate_admin_password
from .schemas import AuditEvent, ChallengeResponse
from .security import (
    MFA_TTL_SECONDS,
    authenticate_user,
    create_mfa_challenge,
    enforce_rate_limit,
    get_current_user,
    pwd_context,
    verify_mfa_challenge,
)


router = APIRouter(prefix="/auth/password", tags=["auth"])


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)


class PasswordChangeConfirm(BaseModel):
    challenge_id: str = Field(min_length=8, max_length=120)
    code: str = Field(min_length=6, max_length=6)
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)


@router.post("/request", response_model=ChallengeResponse)
def request_password_change(
    payload: PasswordChangeRequest,
    request: FastAPIRequest,
    user: dict = Depends(get_current_user),
) -> ChallengeResponse:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="A alteração da palavra-passe administrativa está reservada a administradores.")

    client = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"password-change-request:{client}:{user['email']}", limit=4, window_seconds=600)

    if not authenticate_user(user["email"], payload.current_password):
        record_audit_event(AuditEvent(actor=user["email"], action="ADMIN_PASSWORD_CHANGE_REJECTED", details="Palavra-passe atual incorreta."))
        raise HTTPException(status_code=401, detail="A palavra-passe atual não está correta.")

    challenge_id, development_code, delivery_hint = create_mfa_challenge(user["email"])
    record_audit_event(AuditEvent(actor=user["email"], action="ADMIN_PASSWORD_CHANGE_MFA_CREATED", details="MFA criado para alteração de credenciais."))
    return ChallengeResponse(
        challenge_id=challenge_id,
        expires_in_seconds=MFA_TTL_SECONDS,
        delivery_hint=delivery_hint,
        development_code=development_code,
    )


@router.post("/confirm")
def confirm_password_change(
    payload: PasswordChangeConfirm,
    request: FastAPIRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="A alteração da palavra-passe administrativa está reservada a administradores.")

    client = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"password-change-confirm:{client}:{user['email']}", limit=6, window_seconds=600)

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="A confirmação da nova palavra-passe não coincide.")

    password_errors = validate_admin_password(payload.new_password)
    if password_errors:
        raise HTTPException(status_code=400, detail=" ".join(password_errors))

    authenticated = authenticate_user(user["email"], payload.current_password)
    if not authenticated:
        record_audit_event(AuditEvent(actor=user["email"], action="ADMIN_PASSWORD_CHANGE_REJECTED", details="Palavra-passe atual incorreta na confirmação."))
        raise HTTPException(status_code=401, detail="A palavra-passe atual não está correta.")

    if pwd_context.verify(payload.new_password, authenticated["password_hash"]):
        raise HTTPException(status_code=400, detail="A nova palavra-passe deve ser diferente da atual.")

    verified_user = verify_mfa_challenge(payload.challenge_id, payload.code)
    if not verified_user or verified_user.get("email", "").lower() != user["email"].lower():
        record_audit_event(AuditEvent(actor=user["email"], action="ADMIN_PASSWORD_CHANGE_MFA_FAILED", details="Código MFA inválido ou expirado."))
        raise HTTPException(status_code=401, detail="Código de segurança inválido ou expirado.")

    update_password_hash(user["email"], pwd_context.hash(payload.new_password))
    record_audit_event(AuditEvent(actor=user["email"], action="ADMIN_PASSWORD_CHANGED", details="Palavra-passe administrativa alterada; sessões anteriores invalidadas."))
    return {
        "success": True,
        "message": "Palavra-passe alterada com segurança. Inicie sessão novamente.",
        "reauthenticate": True,
    }
