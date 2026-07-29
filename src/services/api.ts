export const API_BASE_URL = import.meta.env.VITE_SEO_API_URL ?? "http://127.0.0.1:8000";

export async function readJson(response: Response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

export function formatApiError(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") return fallback;
  const detail = (payload as { detail?: unknown }).detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const message = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) return String((item as { msg: unknown }).msg);
        return "";
      })
      .filter(Boolean)
      .join(" ");
    return message || fallback;
  }
  if (detail && typeof detail === "object" && "msg" in detail) {
    return String((detail as { msg: unknown }).msg);
  }
  return fallback;
}

export async function apiRequest<T>(path: string, accessToken: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init.headers ?? {}),
      Authorization: `Bearer ${accessToken}`,
    },
  });
  const payload = await readJson(response);
  if (!response.ok) {
    throw new Error(formatApiError(payload, "Não foi possível concluir a operação."));
  }
  return payload as T;
}
