from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Work traceability UI patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''  preview_bridge?: boolean;
  persistence?: string;
};''',
    '''  preview_bridge?: boolean;
  persistence?: string;
  operational_persistence?: {
    status: string;
    message?: string;
    documentsRegistered?: number;
    severeAnomaliesCreated?: number;
    sourceFileId?: string;
    outputFileId?: string;
    referenceDate?: string | null;
  };
};''',
    "operational persistence result type",
)

text = replace_once(
    text,
    '''  const [workError, setWorkError] = useState("");
  const [result, setResult] = useState<AssistantExecutionResult | null>(null);''',
    '''  const [workError, setWorkError] = useState("");
  const [result, setResult] = useState<AssistantExecutionResult | null>(null);
  const [referenceDate, setReferenceDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [traceabilityMessage, setTraceabilityMessage] = useState("");''',
    "traceability state",
)

text = replace_once(
    text,
    '''  const resultArtifacts = result?.artifacts ?? [];
  const resultChecks = result?.audit?.checks ? Object.entries(result.audit.checks) : [];''',
    '''  const assignReferenceDate = async () => {
    const outputFileId = result?.operational_persistence?.outputFileId;
    if (!outputFileId || !referenceDate) return;
    setTraceabilityMessage("");
    try {
      const form = new FormData();
      form.append("reference_date", referenceDate);
      const response = await fetch(`${API_BASE_URL}/assistant/work/files/${encodeURIComponent(outputFileId)}/reference-date`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: form,
      });
      const payload = await response.json().catch(() => null) as { referenceDate?: string; detail?: string } | null;
      if (!response.ok) throw new Error(payload?.detail || `Não foi possível associar a data (${response.status}).`);
      setResult((current) => current ? {
        ...current,
        operational_persistence: current.operational_persistence ? {
          ...current.operational_persistence,
          referenceDate: payload?.referenceDate || referenceDate,
        } : current.operational_persistence,
      } : current);
      setTraceabilityMessage(`Data de referência ${payload?.referenceDate || referenceDate} guardada na Nuvem.`);
    } catch (error) {
      setTraceabilityMessage(error instanceof Error ? error.message : "Falha ao guardar a data de referência.");
    }
  };

  const resultArtifacts = result?.artifacts ?? [];
  const resultChecks = result?.audit?.checks ? Object.entries(result.audit.checks) : [];''',
    "reference date action",
)

traceability_block = '''                {result.operational_persistence?.status === "PERSISTED" && (
                  <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/[0.06] p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-300">Rastreabilidade operacional</p>
                        <p className="mt-2 text-sm text-emerald-100">{result.operational_persistence.documentsRegistered ?? 0} documento(s) em Documentos · {result.operational_persistence.severeAnomaliesCreated ?? 0} anomalia(s) grave(s) · Excel guardado na Nuvem.</p>
                      </div>
                      {result.operational_persistence.referenceDate && <span className="rounded-full border border-emerald-400/20 px-3 py-1 text-[11px] font-semibold text-emerald-200">Data: {result.operational_persistence.referenceDate}</span>}
                    </div>
                    {result.operational_persistence.outputFileId && (
                      <div className="mt-4 flex flex-wrap items-end gap-2">
                        <label className="min-w-44 flex-1 text-xs font-semibold text-emerald-100/70">Data de referência do Excel na Nuvem<input type="date" value={referenceDate} onChange={(event) => setReferenceDate(event.target.value)} className="mt-2 w-full rounded-xl border border-emerald-400/20 bg-black/20 px-3 py-2 text-sm text-white outline-none" /></label>
                        <button type="button" onClick={() => void assignReferenceDate()} className="rounded-xl bg-emerald-300 px-4 py-2.5 text-sm font-semibold text-emerald-950 hover:bg-emerald-200">Guardar data</button>
                      </div>
                    )}
                    {traceabilityMessage && <p className="mt-3 text-xs text-emerald-100/80">{traceabilityMessage}</p>}
                  </div>
                )}

                {result.operational_persistence?.status === "PENDING_BACKEND_UPGRADE" && (
                  <div className="rounded-2xl border border-amber-400/20 bg-amber-500/[0.06] p-4 text-xs leading-5 text-amber-100"><strong className="text-amber-200">Rastreabilidade preparada:</strong> o executor já está configurado para Documentos → Anomalias → Nuvem, mas a persistência só fica ativa após a atualização do backend no Oracle.</div>
                )}

'''

text = replace_once(
    text,
    '''                {result.preview_bridge && <div className="rounded-2xl border border-blue-400/20 bg-blue-500/[0.06] p-4 text-xs leading-5 text-blue-100"><strong className="text-blue-200">Preview seguro:</strong> a cadeia real de agentes foi executada na branch, sem alterar Production. O histórico deste fallback é temporário; a persistência durável continua reservada ao backend FastAPI.</div>}

                {result.agents_used && result.agents_used.length > 0 && <div className="rounded-2xl border border-white/10 bg-black/15 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]">Agentes utilizados</p><p className="mt-2 text-sm text-[#d6d3d1]">{result.agents_used.join(" → ")}</p></div>}''',
    '''                {result.preview_bridge && <div className="rounded-2xl border border-blue-400/20 bg-blue-500/[0.06] p-4 text-xs leading-5 text-blue-100"><strong className="text-blue-200">Preview seguro:</strong> a cadeia real de agentes foi executada sem alterar Production. Quando o backend de rastreabilidade estiver disponível, a mesma execução também atualiza Documentos, Anomalias e Nuvem.</div>}

''' + traceability_block + '''                {result.agents_used && result.agents_used.length > 0 && <div className="rounded-2xl border border-white/10 bg-black/15 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]">Agentes utilizados</p><p className="mt-2 text-sm text-[#d6d3d1]">{result.agents_used.join(" → ")}</p></div>}''',
    "traceability result block",
)

required_markers = [
    "operational_persistence?:",
    "assignReferenceDate",
    "Rastreabilidade operacional",
    "PENDING_BACKEND_UPGRADE",
    "Data de referência do Excel na Nuvem",
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"Work traceability UI marker missing after patch: {marker}")

path.write_text(text, encoding="utf-8")
print("Added Work traceability status and cloud reference-date control")
