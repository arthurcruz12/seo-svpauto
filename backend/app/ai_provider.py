from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-sol").strip()


def generate_contextual_answer(question: str, metrics: dict, history: list[dict], analysis_level: str = "Elevado") -> str | None:
    if not OPENAI_API_KEY:
        return None
    recent = history[-12:]
    context = "\n".join(f"{item['role']}: {item['content']}" for item in recent)
    instructions = (
        "És a Assistente Operacional SEO de uma empresa portuguesa. Responde sempre em português de Portugal. "
        "Usa apenas os indicadores fornecidos e não inventes valores. Dá uma resposta direta e ações práticas. "
        "Não declares alterações executadas sem confirmação explícita do utilizador. "
        "Distingue claramente factos, cálculos, inferências e dados em falta. "
        "Se o pedido não puder ser respondido com os dados disponíveis, diz exatamente o que falta. "
        f"Nível pedido: {analysis_level}. Em Rápido responde de forma curta; em Elevado inclui conclusão, evidência e próximos passos; "
        "em Auditoria inclui também controlos, exceções e pontos que exigem revisão humana."
    )
    prompt = f"Indicadores atuais: {json.dumps(metrics, ensure_ascii=False)}\nHistórico:\n{context}\nPergunta: {question}"
    request = Request("https://api.openai.com/v1/responses", data=json.dumps({"model": OPENAI_MODEL, "instructions": instructions, "input": prompt}).encode("utf-8"), headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("output_text"):
            return str(result["output_text"]).strip()
        texts = [str(content["text"]) for output in result.get("output", []) for content in output.get("content", []) if content.get("text")]
        return "\n".join(texts).strip() or None
    except Exception:
        return None
