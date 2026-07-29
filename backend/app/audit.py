import hashlib

from .schemas import AuditEvent
from .store import add_audit_event, get_user_by_email, list_audit_events as list_persisted_audit_events


def record_audit_event(event: AuditEvent, company_id: str | None = None) -> dict:
    user = get_user_by_email(event.actor.strip().lower()) if "@" in event.actor else None
    return add_audit_event(
        company_id=company_id or (user["company_id"] if user else "system"),
        actor=pseudonymize_actor(event.actor),
        action=event.action,
        details=event.details,
    )


def list_audit_events(limit: int = 100, company_id: str | None = None) -> list[dict]:
    return list_persisted_audit_events(company_id, limit)


def pseudonymize_actor(actor: str) -> str:
    normalized = actor.strip().lower()
    if "@" not in normalized:
        return normalized or "unknown"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    domain = normalized.split("@", 1)[1]
    return f"user-{digest}@{domain}"
