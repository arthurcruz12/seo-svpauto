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

cloud_trace_helpers = r'''
type AssistantWorkCloudTrace = {
  id: string;
  filename: string;
  contentType: string;
  category: string;
  sizeBytes: number;
  sha256: string;
  uploadedAt: string;
  referenceDate?: string | null;
  taskId?: string | null;
  origin?: string | null;
  parentFileId?: string | null;
};

const assistantWorkTraceability = new Map<string, AssistantWorkCloudTrace>();

function workTraceToCloudFile(item: AssistantWorkCloudTrace): CloudFile {
  return {
    id: item.id,
    filename: item.filename,
    contentType: item.contentType,
    category: item.category,
    sizeBytes: item.sizeBytes,
    sha256: item.sha256,
    uploadedAt: item.uploadedAt,
  };
}

'''
text = replace_once(text, "function App() {", cloud_trace_helpers + "function App() {", "cloud traceability helpers")

text = replace_once(
    text,
    '''  async function loadAssistantCloudFiles(token: string) {''',
    '''  async function loadAssistantWorkTraceability(token: string) {
    if (!token) return;
    try {
      const response = await fetch(`${API_BASE_URL}/assistant/work/files?limit=250`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 404) return;
      if (!response.ok) return;
      const payload = await response.json() as AssistantWorkCloudTrace[];
      payload.forEach((item) => assistantWorkTraceability.set(item.id, item));
      const tracedFiles = payload.map(workTraceToCloudFile);
      const tracedIds = new Set(tracedFiles.map((file) => file.id));
      setCloudFiles((current) => [...tracedFiles, ...current.filter((file) => !tracedIds.has(file.id))]);
    } catch {
      // Oracle may still be on the previous backend; the normal cloud remains usable.
    }
  }

  async function loadAssistantCloudFiles(token: string) {''',
    "work cloud traceability loader",
)

text = replace_once(
    text,
    '''        await refreshCloudState();
        await loadAssistantCloudFiles(accessToken);''',
    '''        await refreshCloudState();
        await loadAssistantWorkTraceability(accessToken);
        await loadAssistantCloudFiles(accessToken);''',
    "cloud traceability refresh",
)

text = replace_once(
    text,
    '''  async function downloadCloudFile(file: CloudFile) {''',
    '''  async function setCloudReferenceDate(fileId: string, date: string) {
    if (!date) {
      showToast("Selecione uma data de referência.");
      return;
    }
    try {
      const form = new FormData();
      form.append("reference_date", date);
      const response = await fetch(`${API_BASE_URL}/assistant/work/files/${encodeURIComponent(fileId)}/reference-date`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: form,
      });
      const payload = await response.json().catch(() => null) as AssistantWorkCloudTrace | { detail?: string } | null;
      if (!response.ok) {
        const detail = payload && "detail" in payload ? payload.detail : undefined;
        throw new Error(detail || "Não foi possível guardar a data de referência.");
      }
      const updated = payload as AssistantWorkCloudTrace;
      assistantWorkTraceability.set(fileId, updated);
      await loadAssistantWorkTraceability(accessToken);
      showToast(`Excel associado a ${new Date(`${date}T12:00:00`).toLocaleDateString("pt-PT")}.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível guardar a data de referência.");
    }
  }

  async function downloadCloudFile(file: CloudFile) {''',
    "cloud reference date action",
)

text = replace_once(
    text,
    '''              onCheckout={startCheckout}
              onDownloadFile={downloadCloudFile}
            />''',
    '''              onCheckout={startCheckout}
              onDownloadFile={downloadCloudFile}
              onSetReferenceDate={setCloudReferenceDate}
            />''',
    "cloud view reference-date handler",
)

text = replace_once(
    text,
    '''  onCheckout,
  onDownloadFile,
}: {''',
    '''  onCheckout,
  onDownloadFile,
  onSetReferenceDate,
}: {''',
    "cloud view prop destructuring",
)

text = replace_once(
    text,
    '''  onCheckout: (plan: string) => void;
  onDownloadFile: (file: CloudFile) => void;
}) {''',
    '''  onCheckout: (plan: string) => void;
  onDownloadFile: (file: CloudFile) => void;
  onSetReferenceDate: (fileId: string, date: string) => void;
}) {''',
    "cloud view prop type",
)

text = replace_once(
    text,
    '''  const latestFile = files[0];
  const storageLabel = totalStorage >= 1024 * 1024 ? `${(totalStorage / (1024 * 1024)).toFixed(1)} MB` : `${(totalStorage / 1024).toFixed(1)} KB`;''',
    '''  const latestFile = files[0];
  const [workReferenceDates, setWorkReferenceDates] = useState<Record<string, string>>({});
  const storageLabel = totalStorage >= 1024 * 1024 ? `${(totalStorage / (1024 * 1024)).toFixed(1)} MB` : `${(totalStorage / 1024).toFixed(1)} KB`;''',
    "cloud date input state",
)

old_cards = '''            {files.map((file) => (
              <button key={file.id} className="rounded-xl border border-line bg-white p-4 text-left transition hover:border-[#0071e3] hover:bg-blue-50/30" onClick={() => onDownloadFile(file)} type="button">
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-[#0071e3]"><FileSpreadsheet size={19} aria-hidden="true" /></span>
                  <Download size={17} className="text-slate-500" aria-hidden="true" />
                </div>
                <p className="mt-3 truncate text-sm font-semibold text-ink">{file.filename}</p>
                <p className="mt-1 text-xs text-slate-500">{file.category} · {(file.sizeBytes / 1024).toFixed(1)} KB</p>
                <p className="mt-1 text-xs text-slate-500">{new Date(file.uploadedAt).toLocaleString("pt-PT")}</p>
                <p className="mt-2 truncate font-mono text-[10px] text-slate-400">SHA-256 {file.sha256}</p>
              </button>
            ))}'''

new_cards = '''            {files.map((file) => {
              const trace = assistantWorkTraceability.get(file.id);
              const isWorkOutput = trace?.origin === "assistant-work-output";
              const selectedReferenceDate = workReferenceDates[file.id] ?? trace?.referenceDate ?? "";
              return (
                <div key={file.id} className={`rounded-xl border bg-white p-4 text-left transition ${isWorkOutput ? "border-emerald-200 hover:border-emerald-400" : "border-line hover:border-[#0071e3]"}`}>
                  <div className="flex items-start justify-between gap-3">
                    <span className={`flex h-10 w-10 items-center justify-center rounded-lg ${isWorkOutput ? "bg-emerald-50 text-emerald-700" : "bg-blue-50 text-[#0071e3]"}`}><FileSpreadsheet size={19} aria-hidden="true" /></span>
                    <button type="button" onClick={() => onDownloadFile(file)} className="rounded-lg border border-black/5 p-2 text-slate-500 hover:bg-slate-50" title="Descarregar ficheiro"><Download size={17} aria-hidden="true" /></button>
                  </div>
                  <p className="mt-3 truncate text-sm font-semibold text-ink">{file.filename}</p>
                  <p className="mt-1 text-xs text-slate-500">{file.category} · {(file.sizeBytes / 1024).toFixed(1)} KB</p>
                  <p className="mt-1 text-xs text-slate-500">Carregado em {new Date(file.uploadedAt).toLocaleString("pt-PT")}</p>
                  {trace?.taskId && <p className="mt-1 truncate text-[10px] font-medium text-slate-400">Tarefa {trace.taskId}</p>}
                  {isWorkOutput && (
                    <div className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3">
                      <p className="text-xs font-semibold text-emerald-900">Data de referência</p>
                      <p className="mt-1 text-[11px] leading-4 text-emerald-800/70">Organiza este Excel no calendário sem alterar as datas originais dos documentos.</p>
                      <div className="mt-2 flex gap-2">
                        <input
                          type="date"
                          value={selectedReferenceDate}
                          max="2099-12-31"
                          onChange={(event) => setWorkReferenceDates((current) => ({ ...current, [file.id]: event.target.value }))}
                          className="min-w-0 flex-1 rounded-lg border border-emerald-200 bg-white px-2 py-2 text-xs text-[#1d1d1f]"
                        />
                        <button
                          type="button"
                          disabled={!selectedReferenceDate}
                          onClick={() => onSetReferenceDate(file.id, selectedReferenceDate)}
                          className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-800 disabled:opacity-40"
                        >
                          Guardar
                        </button>
                      </div>
                      {trace?.referenceDate && <p className="mt-2 text-[11px] font-semibold text-emerald-800">Associado a {new Date(`${trace.referenceDate}T12:00:00`).toLocaleDateString("pt-PT")}</p>}
                    </div>
                  )}
                  <p className="mt-2 truncate font-mono text-[10px] text-slate-400">SHA-256 {file.sha256}</p>
                </div>
              );
            })}'''
text = replace_once(text, old_cards, new_cards, "cloud file reference-date controls")

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
    "loadAssistantWorkTraceability",
    "assistantWorkTraceability",
    "onSetReferenceDate",
    "Organiza este Excel no calendário",
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"Work traceability UI marker missing after patch: {marker}")

path.write_text(text, encoding="utf-8")
print("Added Work traceability controls to Trabalho and Nuvem")
