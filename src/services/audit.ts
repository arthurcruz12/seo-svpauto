export type AuditEvent = {
  id: string;
  at: string;
  actor: string;
  action: string;
  details: string;
};

const auditTrail: AuditEvent[] = [];
let accessToken = "";

export function configurePersistentAudit(token: string) {
  accessToken = token;
}

export function auditAction(action: string, details: string, actor = "utilizador.local") {
  const event: AuditEvent = {
    id: crypto.randomUUID?.() ?? String(Date.now()),
    at: new Date().toISOString(),
    actor,
    action,
    details: redactSensitiveDetails(details),
  };

  auditTrail.unshift(event);
  auditTrail.splice(250);
  if (accessToken) {
    void fetch(`${API_BASE_URL}/audit/events`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ actor, action, details: event.details }),
    }).catch(() => undefined);
  }
  return event;
}

export function getAuditTrail(): AuditEvent[] {
  return [...auditTrail];
}

function redactSensitiveDetails(details: string) {
  return details
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[email]")
    .replace(/\b\d{6}\b/g, "[codigo]");
}
import { API_BASE_URL } from "./api";
