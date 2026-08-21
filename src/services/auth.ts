export type AccountRole = "admin" | "client";

export type LocalAccount = {
  id: string;
  companyId: string;
  companyName: string;
  name: string;
  email: string;
  role: AccountRole;
  permissions: string[];
};

export type SecurityChallenge = {
  id: string;
  expiresAt: number;
  deliveryHint: string;
  developmentCode?: string;
};

export type AuthSession = {
  accessToken: string;
  account: LocalAccount;
};

export const AUTH_SESSION_EVENT = "seo-auth-session";

import { API_BASE_URL, formatApiError, readJson } from "./api";

function apiUnavailableError() {
  return new Error("O serviço SEO está desligado. Execute scripts\\start-local.cmd e volte a tentar.");
}

function mapChallenge(payload: Record<string, unknown>): SecurityChallenge {
  return {
    id: String(payload.challenge_id ?? ""),
    expiresAt: Date.now() + Number(payload.expires_in_seconds ?? 300) * 1000,
    deliveryHint: String(payload.delivery_hint ?? "Código temporário enviado pelo canal seguro configurado."),
    developmentCode: payload.development_code ? String(payload.development_code) : undefined,
  };
}

function publishAuthSession(session: AuthSession) {
  window.dispatchEvent(new CustomEvent<AuthSession>(AUTH_SESSION_EVENT, { detail: session }));
}

export async function authenticateAccount(email: string, password: string): Promise<SecurityChallenge> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(formatApiError(payload, "Email ou palavra-passe inválidos."));
    return mapChallenge(payload);
  } catch (error) {
    throw error instanceof TypeError ? apiUnavailableError() : error;
  }
}

export async function registerClientAccount(input: { name: string; email: string; password: string }) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(formatApiError(payload, "Não foi possível criar a conta."));
  return payload as LocalAccount;
}

export async function verifySecurityCode(challenge: SecurityChallenge, code: string): Promise<AuthSession> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/mfa`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ challenge_id: challenge.id, code }),
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(formatApiError(payload, "Código inválido ou expirado."));
    const session = { accessToken: payload.access_token, account: mapAccount(payload.account) } as AuthSession;
    publishAuthSession(session);
    return session;
  } catch (error) {
    throw error instanceof TypeError ? apiUnavailableError() : error;
  }
}

export async function requestAdminPasswordChange(accessToken: string, currentPassword: string): Promise<SecurityChallenge> {
  const response = await fetch(`${API_BASE_URL}/auth/password/request`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ current_password: currentPassword }),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(formatApiError(payload, "Não foi possível iniciar a alteração da palavra-passe."));
  return mapChallenge(payload);
}

export async function confirmAdminPasswordChange(
  accessToken: string,
  input: {
    challengeId: string;
    code: string;
    currentPassword: string;
    newPassword: string;
    confirmPassword: string;
  },
): Promise<{ success: boolean; message: string; reauthenticate: boolean }> {
  const response = await fetch(`${API_BASE_URL}/auth/password/confirm`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      challenge_id: input.challengeId,
      code: input.code,
      current_password: input.currentPassword,
      new_password: input.newPassword,
      confirm_password: input.confirmPassword,
    }),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(formatApiError(payload, "Não foi possível alterar a palavra-passe."));
  return {
    success: Boolean(payload.success),
    message: String(payload.message ?? "Palavra-passe alterada."),
    reauthenticate: Boolean(payload.reauthenticate),
  };
}

export async function getCurrentAccount(accessToken: string) {
  const response = await fetch(`${API_BASE_URL}/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(formatApiError(payload, "Sessão inválida."));
  return mapAccount(payload);
}

export function hasPermission(account: LocalAccount | null, permission: string) {
  return Boolean(account?.permissions.includes(permission) || account?.permissions.includes("*"));
}

function mapAccount(payload: Record<string, unknown>): LocalAccount {
  return {
    id: String(payload.id ?? ""),
    companyId: String(payload.company_id ?? payload.companyId ?? ""),
    companyName: String(payload.company_name ?? payload.companyName ?? "Empresa"),
    name: String(payload.name ?? ""),
    email: String(payload.email ?? ""),
    role: payload.role === "admin" ? "admin" : "client",
    permissions: Array.isArray(payload.permissions) ? payload.permissions.map(String) : [],
  };
}
