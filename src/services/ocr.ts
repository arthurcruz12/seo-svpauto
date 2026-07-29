import type { OcrResult } from "../domain/types";
import { API_BASE_URL, formatApiError, readJson } from "./api";

export async function readDocumentOcr(accessToken: string, companyId: string, file: File): Promise<OcrResult> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/ocr?company_id=${encodeURIComponent(companyId)}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(formatApiError(payload, "Não foi possível ler o documento."));
  return payload as OcrResult;
}
