from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Work/Tasks UI patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

old_mode_block = '''      {assistantMode === "code" && <AssistantCodePanel />}
      {assistantMode === "integrations" && <AssistantIntegrationsPanel accessToken={accessToken} />}

      <div className={`${assistantMode === "code" || assistantMode === "integrations" ? "hidden " : ""}flex flex-1 flex-col py-8 ${hasAsked ? "justify-between" : "justify-center"}`}>'''
new_mode_block = '''      {assistantMode === "work" && <AssistantWorkPanel accessToken={accessToken} />}
      {assistantMode === "code" && <AssistantCodePanel />}
      {assistantMode === "integrations" && <AssistantIntegrationsPanel accessToken={accessToken} />}

      <div className={`${assistantMode !== "chat" ? "hidden " : ""}flex flex-1 flex-col py-8 ${hasAsked ? "justify-between" : "justify-center"}`}>'''
text = replace_once(text, old_mode_block, new_mode_block, "Trabalho panel routing")

work_panel = r'''
type AssistantTaskArtifact = {
  file_id: string;
  filename: string;
  content_type?: string;
  size?: number;
  sha256?: string;
  download_url?: string;
};

type AssistantTaskRecord = {
  task_id: string;
  agent?: string;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
  status: string;
  progress?: number;
  source_file?: { filename?: string; size?: number };
  output_files?: AssistantTaskArtifact[];
  errors?: string[];
  audit?: {
    valid?: boolean;
    status?: string;
    checks?: Record<string, boolean>;
    failed_checks?: string[];
  } | null;
  agents_used?: string[];
  records_processed?: number;
  records_rejected?: number;
};

type AssistantExecutionResult = {
  answer?: string;
  task_id?: string | null;
  status: string;
  agents_used?: string[];
  artifacts?: AssistantTaskArtifact[];
  audit?: AssistantTaskRecord["audit"];
  confidence?: number;
  errors?: string[];
};

function AssistantWorkPanel({ accessToken }: { accessToken: string }) {
  const workFileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState("Faça a faturação diária deste ficheiro.");
  const [tasks, setTasks] = useState<AssistantTaskRecord[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [workError, setWorkError] = useState("");
  const [result, setResult] = useState<AssistantExecutionResult | null>(null);

  const statusTone = (status: string) => {
    if (status === "COMPLETED") return "bg-emerald-500/15 text-emerald-300 border-emerald-400/20";
    if (status === "FAILED") return "bg-red-500/15 text-red-300 border-red-400/20";
    if (status === "WAITING_APPROVAL") return "bg-amber-500/15 text-amber-300 border-amber-400/20";
    if (status === "RUNNING") return "bg-blue-500/15 text-blue-300 border-blue-400/20";
    return "bg-white/[0.06] text-[#d6d3d1] border-white/10";
  };

  const formatDate = (value?: string) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("pt-PT", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  };

  const loadTasks = async () => {
    setLoadingTasks(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/assistant/tasks`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(payload.detail || `Não foi possível consultar as tarefas (${response.status}).`);
      }
      const payload = await response.json() as { tasks?: AssistantTaskRecord[] };
      setTasks(payload.tasks ?? []);
      setWorkError("");
    } catch (error) {
      setTasks([]);
      setWorkError(error instanceof Error ? error.message : "Não foi possível consultar as tarefas.");
    } finally {
      setLoadingTasks(false);
    }
  };

  useEffect(() => {
    void loadTasks();
  }, [accessToken]);

  const downloadArtifact = async (artifact: AssistantTaskArtifact) => {
    if (!artifact.download_url) return;
    setWorkError("");
    try {
      const url = artifact.download_url.startsWith("/api/")
        ? `${API_BASE_URL}${artifact.download_url}`
        : artifact.download_url;
      const response = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (!response.ok) throw new Error(`Não foi possível descarregar o ficheiro (${response.status}).`);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = artifact.filename || "resultado.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (error) {
      setWorkError(error instanceof Error ? error.message : "Falha ao descarregar o ficheiro.");
    }
  };

  const executeTask = async () => {
    if (!selectedFile || executing) return;
    setExecuting(true);
    setWorkError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("message", message.trim() || "Faça a faturação diária deste ficheiro.");
      form.append("file", selectedFile);
      const response = await fetch(`${API_BASE_URL}/api/v1/assistant/messages`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: form,
      });
      const payload = await response.json().catch(() => null) as AssistantExecutionResult | null;
      if (!response.ok || !payload) {
        throw new Error(`Não foi possível executar a tarefa (${response.status}).`);
      }
      setResult(payload);
      if (payload.status === "COMPLETED") setSelectedFile(null);
      await loadTasks();
    } catch (error) {
      setWorkError(error instanceof Error ? error.message : "Não foi possível executar a tarefa.");
    } finally {
      setExecuting(false);
    }
  };

  const resultArtifacts = result?.artifacts ?? [];
  const resultChecks = result?.audit?.checks ? Object.entries(result.audit.checks) : [];

  return (
    <div className="flex flex-1 flex-col py-8">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-300">Assistente IA · Trabalho</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Executar e acompanhar tarefas</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#a8a29e]">Nesta fase, o fluxo executável é a faturação diária: DocumentAgent → BillingAgent → AuditAgent. O resultado só fica disponível quando a auditoria aprova o Excel.</p>
          </div>
          <button type="button" onClick={() => void loadTasks()} disabled={loadingTasks} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm font-semibold text-[#d6d3d1] transition hover:bg-white/[0.06] disabled:cursor-wait disabled:opacity-50">
            {loadingTasks ? "A atualizar…" : "Atualizar tarefas"}
          </button>
        </div>

        {workError && (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm leading-6 text-red-200">
            <p className="font-semibold">Trabalho indisponível neste ambiente</p>
            <p className="mt-1">{workError}</p>
          </div>
        )}

        <div className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
          <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-400">Nova tarefa</p>
                <h3 className="mt-2 text-lg font-semibold text-white">Faturação diária</h3>
              </div>
              <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold text-emerald-300">Executor real</span>
            </div>

            <input
              ref={workFileRef}
              className="hidden"
              type="file"
              accept=".xlsx,.xlsm,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null);
                setResult(null);
                setWorkError("");
                event.currentTarget.value = "";
              }}
            />

            <button type="button" onClick={() => workFileRef.current?.click()} className="mt-5 flex w-full items-center gap-4 rounded-2xl border border-dashed border-white/15 bg-black/20 p-5 text-left transition hover:border-blue-400/30 hover:bg-blue-500/[0.04]">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300"><Upload size={22} /></span>
              <span className="min-w-0">
                <strong className="block truncate text-sm text-white">{selectedFile?.name ?? "Selecionar Excel bruto"}</strong>
                <span className="mt-1 block text-xs text-[#a8a29e]">{selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB · pronto para executar` : "XLSX/XLSM · o original é preservado"}</span>
              </span>
            </button>

            <label className="mt-5 block text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]" htmlFor="work-task-message">Instrução</label>
            <textarea id="work-task-message" value={message} onChange={(event) => setMessage(event.target.value)} className="mt-2 min-h-24 w-full resize-none rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm leading-6 text-white outline-none placeholder:text-[#78716c] focus:border-blue-400/30" placeholder="Descreva o trabalho que pretende executar" />

            {executing && (
              <div className="mt-4 rounded-2xl border border-blue-400/20 bg-blue-500/[0.06] p-4">
                <div className="flex items-center gap-3 text-sm font-semibold text-blue-200"><span className="h-2 w-2 animate-pulse rounded-full bg-blue-300" />A executar a tarefa</div>
                <div className="mt-4 grid gap-2 sm:grid-cols-3">
                  {["DocumentAgent", "BillingAgent", "AuditAgent"].map((agent) => <div key={agent} className="rounded-xl border border-white/10 bg-black/15 px-3 py-2 text-xs text-[#d6d3d1]">{agent}</div>)}
                </div>
              </div>
            )}

            <button type="button" disabled={!selectedFile || executing} onClick={() => void executeTask()} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-black transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-40">
              <Bot size={17} />{executing ? "A executar…" : "Executar com Agent Manager"}
            </button>
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#78716c]">Resultado mais recente</p>
            {!result && !executing && <div className="mt-5 rounded-2xl border border-dashed border-white/10 p-6 text-center"><ClipboardCheck className="mx-auto text-[#78716c]" size={30} /><p className="mt-3 text-sm font-semibold text-white">Nenhuma execução nesta sessão</p><p className="mt-1 text-xs leading-5 text-[#78716c]">Selecione um Excel e execute a tarefa. O auditor decide se o resultado pode ser disponibilizado.</p></div>}
            {result && (
              <div className="mt-4 space-y-4">
                <div className={`rounded-2xl border p-4 ${statusTone(result.status)}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold">{result.status === "COMPLETED" ? "Trabalho concluído" : result.status === "FAILED" ? "Trabalho rejeitado" : result.status}</p>
                    {result.task_id && <span className="text-[10px] opacity-70">#{result.task_id.slice(0, 8)}</span>}
                  </div>
                  {result.answer && <p className="mt-2 text-sm leading-6 opacity-90">{result.answer}</p>}
                </div>

                {result.agents_used && result.agents_used.length > 0 && <div className="rounded-2xl border border-white/10 bg-black/15 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#78716c]">Agentes utilizados</p><p className="mt-2 text-sm text-[#d6d3d1]">{result.agents_used.join(" → ")}</p></div>}

                {resultArtifacts.map((artifact) => (
                  <div key={artifact.file_id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-500/[0.06] p-4">
                    <div className="min-w-0"><p className="truncate text-sm font-semibold text-emerald-200">{artifact.filename}</p><p className="mt-1 text-xs text-emerald-100/60">3 folhas obrigatórias · resultado auditado</p></div>
                    <button type="button" onClick={() => void downloadArtifact(artifact)} className="flex items-center gap-2 rounded-full bg-emerald-400 px-4 py-2 text-sm font-semibold text-emerald-950 hover:bg-emerald-300"><Download size={16} />Descarregar</button>
                  </div>
                ))}

                {resultChecks.length > 0 && (
                  <details className="rounded-2xl border border-white/10 bg-black/15 p-4">
                    <summary className="cursor-pointer text-sm font-semibold text-[#d6d3d1]">Ver auditoria ({resultChecks.filter(([, passed]) => passed).length}/{resultChecks.length})</summary>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">{resultChecks.map(([check, passed]) => <div key={check} className="flex items-center gap-2 text-xs text-[#a8a29e]">{passed ? <CheckCircle2 size={14} className="text-emerald-400" /> : <AlertTriangle size={14} className="text-red-300" />}<span>{check}</span></div>)}</div>
                  </details>
                )}

                {result.errors && result.errors.length > 0 && <div className="rounded-2xl border border-red-400/20 bg-red-500/[0.06] p-4 text-xs leading-5 text-red-200">{result.errors.join(" · ")}</div>}
              </div>
            )}
          </section>
        </div>

        <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#78716c]">Histórico</p><h3 className="mt-2 text-lg font-semibold text-white">Tarefas recentes</h3></div>
            <span className="text-xs text-[#78716c]">{tasks.length} tarefa(s)</span>
          </div>

          {loadingTasks ? (
            <div className="mt-5 flex items-center gap-3 text-sm text-[#a8a29e]"><span className="h-2 w-2 animate-pulse rounded-full bg-blue-300" />A carregar tarefas…</div>
          ) : tasks.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-dashed border-white/10 p-6 text-center text-sm text-[#78716c]">Ainda não existem tarefas guardadas para este utilizador/tenant.</div>
          ) : (
            <div className="mt-5 space-y-3">
              {tasks.slice(0, 20).map((task) => (
                <article key={task.task_id} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2"><span className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold ${statusTone(task.status)}`}>{task.status}</span><span className="text-[11px] text-[#78716c]">{formatDate(task.created_at)}</span></div>
                      <p className="mt-3 truncate text-sm font-semibold text-white">{task.source_file?.filename ?? "Faturação diária"}</p>
                      <p className="mt-1 text-xs text-[#a8a29e]">{task.records_processed ?? 0} processados · {task.records_rejected ?? 0} rejeitados{task.agents_used?.length ? ` · ${task.agents_used.join(" → ")}` : ""}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(task.output_files ?? []).map((artifact) => <button key={artifact.file_id} type="button" onClick={() => void downloadArtifact(artifact)} className="flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/15"><Download size={14} />Excel</button>)}
                    </div>
                  </div>
                  {task.errors && task.errors.length > 0 && <p className="mt-3 text-xs leading-5 text-red-200">{task.errors.join(" · ")}</p>}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

'''

text = replace_once(text, "function AssistantCodePanel() {", work_panel + "function AssistantCodePanel() {", "AssistantWorkPanel injection")

required_markers = [
    'function AssistantWorkPanel({ accessToken }',
    '/api/v1/assistant/messages',
    '/api/v1/assistant/tasks',
    'Descarregar',
    'DocumentAgent',
    'BillingAgent',
    'AuditAgent',
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"Work/Tasks UI marker missing after patch: {marker}")

path.write_text(text, encoding="utf-8")
print("Connected Assistente IA > Trabalho to executable tasks API")
