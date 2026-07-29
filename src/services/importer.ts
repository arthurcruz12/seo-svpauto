import type { ClassifiedMovement, ImportedDataset } from "../domain/types";
import { API_BASE_URL, formatApiError, readJson } from "./api";

export const MAX_UPLOAD_SIZE_MB = 50;
export const OPERATIONAL_FILE_EXTENSIONS = ["xlsx", "pdf", "csv", "txt", "xml", "jpg", "jpeg", "png"];
export const TEXT_FILE_EXTENSIONS = ["csv", "txt"];

export async function buildOperationalDatasetFromFile(file: File, accessToken?: string, signal?: AbortSignal): Promise<ImportedDataset> {
  return buildOperationalDatasetFromBackend(file, accessToken, signal);
}

export function validateUploadFile(file: File, allowedExtensions: string[]) {
  const extension = getFileExtension(file.name);
  if (!extension || !allowedExtensions.includes(extension)) {
    return `Formato inválido. Use apenas: ${allowedExtensions.join(", ")}.`;
  }

  const sizeMb = file.size / (1024 * 1024);
  if (sizeMb > MAX_UPLOAD_SIZE_MB) {
    return `Ficheiro demasiado grande. O limite atual é ${MAX_UPLOAD_SIZE_MB} MB.`;
  }

  return "";
}

async function buildOperationalDatasetFromBackend(file: File, accessToken?: string, signal?: AbortSignal): Promise<ImportedDataset> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE_URL}/files/analyze`, {
    method: "POST",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    body: form,
    signal,
  });
  const payload = await readJson(response);
  if (!response.ok) {
    throw new Error(formatApiError(payload, "Não foi possível processar o ficheiro no servidor."));
  }
  return payload as ImportedDataset;
}

export function buildPlatformChartData(movements: ClassifiedMovement[]) {
  const grouped = new Map<string, { receita: number; custo: number }>();

  movements.forEach((movement) => {
    const channel = inferSalesChannel(movement);
    const current = grouped.get(channel) ?? { receita: 0, custo: 0 };

    if (["71", "72", "78"].includes(movement.accountCode)) {
      current.receita += Math.abs(movement.amount);
    }
    if (["22", "24", "31", "62", "63", "68"].includes(movement.accountCode)) {
      current.custo += Math.abs(movement.amount);
    }

    grouped.set(channel, current);
  });

  return Array.from(grouped.entries())
    .map(([name, values]) => ({
      name,
      receita: Number(values.receita.toFixed(2)),
      margem: values.receita > 0 ? Number((((values.receita - values.custo) / values.receita) * 100).toFixed(1)) : 0,
    }))
    .filter((item) => item.receita > 0)
    .sort((a, b) => b.receita - a.receita)
    .slice(0, 6);
}

export function buildMonthlyChartData(movements: ClassifiedMovement[]) {
  const grouped = new Map<string, { sales: number; expenses: number; label: string }>();

  movements.forEach((movement) => {
    const key = getMonthKey(movement.date);
    const current = grouped.get(key) ?? { sales: 0, expenses: 0, label: getMonthLabel(movement.date) };
    if (["71", "72", "78"].includes(movement.accountCode)) {
      current.sales += Math.abs(movement.amount);
    }
    if (["22", "24", "31", "62", "63", "68"].includes(movement.accountCode)) {
      current.expenses += Math.abs(movement.amount);
    }
    grouped.set(key, current);
  });

  return Array.from(grouped.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, values]) => ({
      month: values.label,
      vendas: Number(values.sales.toFixed(2)),
      margem: values.sales > 0 ? Number((((values.sales - values.expenses) / values.sales) * 100).toFixed(1)) : 0,
    }));
}

function inferSalesChannel(movement: ClassifiedMovement) {
  const text = normalizeText(`${movement.description} ${movement.entity}`);
  if (text.includes("ovoko")) return "Ovoko";
  if (text.includes("recambio")) return "Recambio";
  if (text.includes("online") || text.includes("site") || text.includes("web")) return "Loja online";
  if (text.includes("loja") || text.includes("balcao") || text.includes("balcão")) return "Loja física";
  if (movement.entity && movement.entity !== "Não identificado") return movement.entity.slice(0, 18);
  return "Outros";
}

function getMonthKey(date: string) {
  const normalized = normalizeDateForMonth(date);
  const match = normalized.match(/^(\d{4})-(\d{1,2})/);
  if (!match) return "sem-data";
  return `${match[1]}-${match[2].padStart(2, "0")}`;
}

function getMonthLabel(date: string) {
  const normalized = normalizeDateForMonth(date);
  const match = normalized.match(/^(\d{4})-(\d{1,2})/);
  if (!match) return "Sem data";
  const monthIndex = Number(match[2]) - 1;
  return ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"][monthIndex] ?? "Mês";
}

function normalizeDateForMonth(date: string) {
  const european = date.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
  if (european) {
    const year = european[3].length === 2 ? `20${european[3]}` : european[3];
    return `${year}-${european[2].padStart(2, "0")}-${european[1].padStart(2, "0")}`;
  }
  return date;
}

function getFileExtension(fileName: string) {
  return fileName.split(".").pop()?.toLowerCase() || "";
}

function normalizeText(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}
