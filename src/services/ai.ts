import type { AiAnalysis } from "../domain/types";
import { API_BASE_URL, formatApiError, readJson } from "./api";

export async function askBackendAi(accessToken: string, question: string, conversationId?: string, analysisLevel = "Elevado"): Promise<AiAnalysis> {
  const response = await fetch(`${API_BASE_URL}/ai/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ question, conversation_id: conversationId, analysis_level: analysisLevel }),
  });
  const payload = await readJson(response);
  if (!response.ok) throw new Error(formatApiError(payload, "Não foi possível consultar a IA."));
  return {
    answer: payload.answer,
    confidence: payload.confidence,
    risk: payload.risk,
    priorities: payload.priorities,
    actions: payload.actions,
    intent: payload.intent,
    nextQuestions: payload.nextQuestions,
    conversationId: payload.conversationId,
    provider: payload.provider,
    explainability: payload.explainability,
  };
}
