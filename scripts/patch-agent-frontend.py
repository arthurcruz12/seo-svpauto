from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Protected frontend patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig")

# The login, administrator credentials, authentication handlers, landing page
# and public navigation are deliberately untouched. All patches are scoped to
# the existing AiView component and its invocation.
text = replace_once(
    text,
    "              analysis={aiAnalysis}\n              onQuestionChange={setAiQuestion}",
    "              analysis={aiAnalysis}\n              accessToken={accessToken}\n              onQuestionChange={setAiQuestion}",
    "AiView access token",
)

text = replace_once(
    text,
    "function AiView({\n  question,\n  analysis,",
    "function AiView({\n  question,\n  analysis,\n  accessToken,",
    "AiView props destructuring",
)

text = replace_once(
    text,
    "  question: string;\n  analysis: AiAnalysis;",
    "  question: string;\n  analysis: AiAnalysis;\n  accessToken: string;",
    "AiView access token type",
)

text = replace_once(
    text,
    '  const [assistantMode, setAssistantMode] = useState<"chat" | "work">("chat");',
    '''  const [assistantMode, setAssistantMode] = useState<"chat" | "work" | "code" | "integrations">("chat");
  const [agentRoute, setAgentRoute] = useState<{
    task_id: string;
    manager: string;
    agents: string[];
    reasons: string[];
    approval_required: boolean;
    write_blocked: boolean;
  } | null>(null);''',
    "assistant mode state",
)

text = replace_once(
    text,
    '''      <div className="mx-auto flex rounded-full bg-white/[0.06] p-1">
        {(["chat", "work"] as const).map((mode) => (
          <button key={mode} type="button" onClick={() => setAssistantMode(mode)} className={`min-w-32 rounded-full px-8 py-3 text-sm font-semibold transition ${assistantMode === mode ? "bg-white/[0.08] text-white" : "text-[#a38476] hover:text-white"}`}>
            {mode === "chat" ? "Chat" : "Trabalho"}
          </button>
        ))}
      </div>

      <div className={`flex flex-1 flex-col py-8 ${hasAsked ? "justify-between" : "justify-center"}`}>''',
    '''      <div className="mx-auto flex flex-wrap justify-center rounded-2xl bg-white/[0.06] p-1">
        {(["chat", "work", "code", "integrations"] as const).map((mode) => (
          <button key={mode} type="button" onClick={() => setAssistantMode(mode)} className={`min-w-28 rounded-xl px-5 py-3 text-sm font-semibold transition ${assistantMode === mode ? "bg-white/[0.08] text-white" : "text-[#a38476] hover:text-white"}`}>
            {mode === "chat" ? "Chat" : mode === "work" ? "Trabalho" : mode === "code" ? "Código" : "Integrações"}
          </button>
        ))}
      </div>

      {assistantMode === "code" && <AssistantCodePanel />}
      {assistantMode === "integrations" && <AssistantIntegrationsPanel accessToken={accessToken} />}

      <div className={`${assistantMode === "code" || assistantMode === "integrations" ? "hidden " : ""}flex flex-1 flex-col py-8 ${hasAsked ? "justify-between" : "justify-center"}`}>''',
    "assistant tabs",
)

text = replace_once(
    text,
    '''    const submittedAt = new Date();
    if (responseDate && lastSubmittedQuestion) {''',
    '''    const submittedAt = new Date();
    try {
      const routeResponse = await fetch(`${API_BASE_URL}/api/v1/agents/route`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ message: submittedQuestion, mode: assistantMode }),
      });
      if (routeResponse.ok) {
        setAgentRoute(await routeResponse.json());
      } else {
        setAgentRoute(null);
      }
    } catch {
      // Agent routing is additive. A temporary routing outage must not break
      // the existing Assistant IA conversation/workflow.
      setAgentRoute(null);
    }
    if (responseDate && lastSubmittedQuestion) {''',
    "agent manager routing",
)

text = replace_once(
    text,
    '''                  <p className="text-sm leading-7 text-[#d6d3d1]">{analysis.answer}</p>''',
    '''                  {agentRoute && (
                    <div className="rounded-2xl border border-blue-400/20 bg-blue-500/[0.06] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-300">SEO Agent Manager</p>
                        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${agentRoute.write_blocked ? "bg-amber-500/15 text-amber-300" : "bg-emerald-500/15 text-emerald-300"}`}>
                          {agentRoute.approval_required ? "Aprovação humana necessária" : "Roteamento seguro"}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-[#d6d3d1]">Agentes: {agentRoute.agents.join(" → ")}</p>
                      {agentRoute.reasons[0] && <p className="mt-2 text-xs leading-5 text-[#a8a29e]">{agentRoute.reasons[0]}</p>}
                    </div>
                  )}
                  <p className="text-sm leading-7 text-[#d6d3d1]">{analysis.answer}</p>''',
    "agent routing result card",
)

panels = r'''

function AssistantCodePanel() {
  return (
    <div className="flex flex-1 flex-col py-8">
      <div className="mx-auto w-full max-w-5xl space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-300">Assistente IA · Código</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Engenharia assistida pelos agentes</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#a8a29e]">O Agent Manager encaminha tarefas técnicas para o Agente de Código. Codex e GitHub são ferramentas especializadas; não substituem o Agent Manager operacional do SEO.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
            <p className="text-sm font-semibold text-white">Codex</p>
            <p className="mt-2 text-sm leading-6 text-[#a8a29e]">Análise de código, correções, patches, testes e implementação técnica.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
            <p className="text-sm font-semibold text-white">GitHub</p>
            <p className="mt-2 text-sm leading-6 text-[#a8a29e]">Repositório, branches, pull requests, revisão e CI/CD com rastreabilidade.</p>
          </div>
          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/[0.05] p-5">
            <p className="flex items-center gap-2 text-sm font-semibold text-emerald-300"><ShieldCheck size={17} /> Proteção do sistema</p>
            <p className="mt-2 text-sm leading-6 text-[#a8a29e]">Homepage, login, autenticação e credenciais do administrador são áreas protegidas e não podem ser alteradas por uma tarefa genérica de agentes.</p>
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-[#0b0d0e] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#78716c]">Fluxo</p>
          <p className="mt-3 text-sm leading-7 text-[#d6d3d1]">Pedido técnico → SEO Agent Manager → Agente de Código → Codex/GitHub → testes → resultado → auditoria.</p>
        </div>
      </div>
    </div>
  );
}

function AssistantIntegrationsPanel({ accessToken }: { accessToken: string }) {
  const [integrations, setIntegrations] = useState<Array<{
    id: string;
    name: string;
    category: string;
    configured: boolean;
    status: string;
    permissions?: string[];
    agents?: string[];
    note?: string;
    approval_required?: boolean;
  }>>([]);
  const [managerStatus, setManagerStatus] = useState<{ enabled?: boolean; execution_enabled?: boolean; memory_enabled?: boolean; write_policy?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const headers = { Authorization: `Bearer ${accessToken}` };
        const [integrationResponse, statusResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/v1/agents/integrations`, { headers }),
          fetch(`${API_BASE_URL}/api/v1/agents/status`, { headers }),
        ]);
        if (!integrationResponse.ok || !statusResponse.ok) throw new Error("Não foi possível consultar as integrações dos agentes.");
        const integrationPayload = await integrationResponse.json() as { integrations?: typeof integrations };
        const statusPayload = await statusResponse.json() as typeof managerStatus;
        if (!cancelled) {
          setIntegrations(integrationPayload.integrations ?? []);
          setManagerStatus(statusPayload);
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "Falha ao consultar integrações.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [accessToken]);

  const categories = Array.from(new Set(integrations.map((item) => item.category)));

  return (
    <div className="flex flex-1 flex-col py-8">
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-300">Assistente IA · Integrações</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Ferramentas disponíveis para os agentes</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#a8a29e]">As integrações ficam dentro da Assistente IA, depois de Código. Nenhum token, palavra-passe, API key ou connection string é mostrado nesta página.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] px-4 py-3 text-xs text-[#d6d3d1]">
            <p><strong className="text-white">Agent Manager:</strong> {managerStatus?.enabled === false ? "desativado" : "ativo"}</p>
            <p className="mt-1"><strong className="text-white">Escrita automática:</strong> {managerStatus?.execution_enabled ? "habilitada com política" : "bloqueada"}</p>
          </div>
        </div>

        <div className="rounded-2xl border border-amber-400/20 bg-amber-500/[0.05] p-4 text-sm leading-6 text-[#d6d3d1]">
          <strong className="text-amber-300">Separação obrigatória:</strong> Atena é uma fonte confiável de informação. SNC é a camada contabilística. São integrações diferentes e não devem ser tratadas como o mesmo sistema.
        </div>

        {loading && <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5 text-sm text-[#a8a29e]">A verificar integrações…</div>}
        {error && <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-200">{error}</div>}

        {!loading && !error && categories.map((category) => (
          <section key={category} className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#78716c]">{category}</p>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {integrations.filter((item) => item.category === category).map((item) => (
                <div key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.025] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-white">{item.name}</p>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${item.configured ? "bg-emerald-500/15 text-emerald-300" : "bg-white/[0.06] text-[#a8a29e]"}`}>{item.status}</span>
                  </div>
                  {item.permissions && item.permissions.length > 0 && <p className="mt-3 text-xs text-[#a8a29e]">Permissões: {item.permissions.join(" · ")}</p>}
                  {item.agents && item.agents.length > 0 && <p className="mt-2 text-xs text-[#78716c]">Agentes: {item.agents.join(", ")}</p>}
                  {item.approval_required && <p className="mt-2 text-xs font-medium text-amber-300">Escrita exige aprovação humana.</p>}
                  {item.note && <p className="mt-2 text-xs leading-5 text-[#a8a29e]">{item.note}</p>}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
'''

text = replace_once(text, "\nexport default App;", panels + "\nexport default App;", "assistant support panels")

# Guardrails: ensure protected public/authentication markers remain present.
protected_markers = [
    'const [appScreen, setAppScreen] = useState<AppScreen>("landing")',
    'async function handleLogin(event: FormEvent<HTMLFormElement>)',
    'async function handleMfa(event: FormEvent<HTMLFormElement>)',
    'async function handleRegister(event: FormEvent<HTMLFormElement>)',
    'admin@seo.local',
    'Registrar conta de cliente',
]
for marker in protected_markers:
    if marker not in text:
        raise SystemExit(f"Protected frontend marker missing after patch: {marker}")

path.write_text(text, encoding="utf-8")
print("Patched Assistant IA only: Chat | Trabalho | Código | Integrações")
